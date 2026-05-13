"""
TenderSight Orchestrator Agent v3.0 — Manages the full evaluation pipeline.

Pipeline:
  1. Ingest tender document/bundle (smart OCR + ZIP support)
  2. Extract GeM metadata deterministically (zero LLM cost)
  3. Extract eligibility criteria
  4. For each bidder:
     a. Security scan
     b. Ingest bidder document (smart OCR)
     c. Run GFR 2017 exemption checks (MSME/Startup — zero LLM cost)
     d. Combined evidence + evaluation (single LLM call)
     e. Reviewer pass (borderline verdicts only)
  5. Provenance DAG tracks every step for audit trail
"""
import logging
from typing import Dict, List, Optional
from agents.base import BaseAgent, AgentInput, AgentOutput
from agents.ingestion_agent import ingest_document
from agents.security_agent import check_security
from agents.criteria_agent import extract_criteria
from agents.judge_agent import evaluate_bidder
from agents.deterministic_engine import (
    ProcurementRulesEngine, extract_gem_metadata, extract_certifications,
)
from utils.provenance import get_or_create_dag
from utils.bundle_processor import (
    process_zip_to_bundle, process_boq_in_bundle, TenderBundle,
)

logger = logging.getLogger(__name__)


class OrchestratorAgent(BaseAgent):
    """Manages the full TenderSight evaluation pipeline."""

    def __init__(self):
        super().__init__("OrchestratorAgent")

    async def execute(self, input_data: AgentInput) -> AgentOutput:
        """Not used directly — use run_pipeline instead."""
        return AgentOutput(status="success", result={})

    def process_tender(self, file_bytes, filename, api_key=None, progress_callback=None, tender_id=""):
        """Step 1: Ingest tender document/bundle and extract criteria. Supports ZIP bundles."""
        dag = get_or_create_dag(tender_id) if tender_id else None
        is_zip = filename.lower().endswith(".zip")
        bundle_info = None

        if is_zip:
            if progress_callback:
                progress_callback("Extracting tender bundle from ZIP...")
            bundle = process_zip_to_bundle(file_bytes, tender_id=tender_id)
            if dag:
                doc_types = {d.filename: d.doc_type for d in bundle.documents}
                bundle_node = dag.record_bundle_upload([d.filename for d in bundle.documents], doc_types)

            for doc in bundle.documents:
                if progress_callback:
                    progress_callback(f"Ingesting [{doc.doc_type.upper()}] {doc.filename}...")
                ingestion = ingest_document(doc.raw_bytes, doc.filename, api_key=api_key, progress_callback=progress_callback)
                doc.extracted_text = ingestion["raw_text"]
                doc.char_count = len(doc.extracted_text)
                if dag:
                    dag.record_ingestion(doc.filename, doc.doc_type, ingestion["ocr_engine"],
                                         ingestion["confidence"], doc.char_count,
                                         parent_ids=[bundle_node.node_id] if bundle_node else None)

            process_boq_in_bundle(bundle)
            full_text = bundle.get_unified_text()
            bundle_info = bundle.get_summary()
            ocr_engine = "bundle"
            confidence = 0.90
            pages = 0
        else:
            if progress_callback:
                progress_callback("Ingesting tender document...")
            ingestion = ingest_document(file_bytes, filename, api_key=api_key, progress_callback=progress_callback)
            if not ingestion["raw_text"] or ingestion["confidence"] == 0.0:
                raise ValueError(f"Could not extract text from tender document ({ingestion['ocr_engine']})")
            full_text = ingestion["raw_text"]
            ocr_engine = ingestion["ocr_engine"]
            confidence = ingestion["confidence"]
            pages = ingestion.get("pages", 0)
            if dag:
                dag.record_ingestion(filename, "rfp", ocr_engine, confidence, len(full_text))

        if progress_callback:
            progress_callback(f"Text extracted ({ocr_engine}, {confidence:.0%} confidence)")

        # GeM Metadata Extraction (zero LLM cost)
        gem_metadata = extract_gem_metadata(full_text)

        # Extract Criteria
        if progress_callback:
            progress_callback("Extracting eligibility criteria...")
        criteria = extract_criteria(full_text, api_key=api_key, progress_callback=progress_callback)
        if dag:
            dag.record_criteria_extraction([str(c.get("id", "")) for c in criteria], source_doc=filename)

        result = {"raw_text": full_text, "criteria": criteria, "ocr_engine": ocr_engine,
                  "confidence": confidence, "pages": pages, "gem_metadata": gem_metadata}
        if bundle_info:
            result["bundle_info"] = bundle_info
        return result

    def evaluate_single_bidder(self, criteria, bidder_name, bidder_bytes_list, bidder_filenames,
                                api_key=None, progress_callback=None, tender_id=""):
        """Evaluate a single bidder: Security -> Ingest -> GFR Rules -> LLM Evaluate."""
        dag = get_or_create_dag(tender_id) if tender_id else None

        # 1. Ingest bidder documents
        if progress_callback:
            progress_callback(f"Ingesting {bidder_name}'s documents...")
        master_bidder_text = ""
        overall_confidence = 0.0
        used_engine = "unknown"
        for b_bytes, b_fname in zip(bidder_bytes_list, bidder_filenames):
            ingestion = ingest_document(b_bytes, b_fname, api_key=api_key, progress_callback=progress_callback)
            master_bidder_text += f"\n\n--- Document: {b_fname} ---\n\n{ingestion['raw_text']}"
            overall_confidence += ingestion["confidence"]
            used_engine = ingestion["ocr_engine"]
        if not master_bidder_text.strip():
            return {"bidder_name": bidder_name, "overall_status": "MANUAL_REVIEW", "verdicts": [],
                    "eligible_count": 0, "not_eligible_count": 0,
                    "manual_review_count": len(criteria), "error": "Could not extract text", "ocr_engine": used_engine}
        overall_confidence /= len(bidder_bytes_list) if bidder_bytes_list else 1

        # 2. Security scan
        if progress_callback:
            progress_callback(f"Security scanning {bidder_name}...")
        security = check_security(master_bidder_text, filename="Multiple Documents")
        if dag:
            dag.record_security_scan(bidder_name, security.get("safe", True), security.get("threats_detected", []))
        if not security.get("safe", True):
            return {"bidder_name": bidder_name, "overall_status": "NOT_ELIGIBLE", "verdicts": [],
                    "eligible_count": 0, "not_eligible_count": len(criteria), "manual_review_count": 0,
                    "error": f"Security threat: {security.get('threats_detected', [])}",
                    "security_report": security, "ocr_engine": used_engine}

        # 3. GFR 2017 Procurement Rules (zero LLM cost)
        if progress_callback:
            progress_callback(f"Checking GFR 2017 exemptions for {bidder_name}...")
        rules_engine = ProcurementRulesEngine()
        msme_status = rules_engine.detect_msme_status(master_bidder_text)
        startup_status = rules_engine.detect_startup_status(master_bidder_text)
        mii_status = rules_engine.detect_make_in_india(master_bidder_text)
        certifications = extract_certifications(master_bidder_text)

        gfr_exemptions = {}
        for c in criteria:
            exemption = rules_engine.check_exemptions_for_criterion(c, msme_status, startup_status)
            if exemption:
                cid = str(c.get("id", ""))
                gfr_exemptions[cid] = exemption
                if dag:
                    dag.record_gfr_exemption(bidder_name, cid, exemption["exemption_type"],
                                              exemption.get("certificate_ref", ""), exemption.get("gfr_rule", ""))

        if gfr_exemptions and progress_callback:
            progress_callback(f"{len(gfr_exemptions)} criteria resolved by GFR rules (zero LLM cost)")

        # 4. LLM evaluation
        if progress_callback:
            progress_callback(f"Evaluating {bidder_name}...")
        evaluation = evaluate_bidder(criteria, master_bidder_text, bidder_name,
                                     api_key=api_key, progress_callback=progress_callback)

        # 5. Overlay GFR exemptions onto LLM verdicts
        for v in evaluation.get("verdicts", []):
            cid = v.get("criterion_id", "")
            if cid in gfr_exemptions:
                ex = gfr_exemptions[cid]
                v["status"] = ex["status"]
                v["confidence"] = ex["confidence"]
                v["reasoning"] = ex["reasoning"]
                v["pass_used"] = "gfr_rules_engine"
                v["gfr_exemption"] = {"type": ex["exemption_type"], "rule": ex.get("gfr_rule", ""),
                                       "certificate": ex.get("certificate_ref", "")}

        # Recompute aggregates
        statuses = [v["status"] for v in evaluation.get("verdicts", [])]
        evaluation["eligible_count"] = statuses.count("ELIGIBLE")
        evaluation["not_eligible_count"] = statuses.count("NOT_ELIGIBLE")
        evaluation["manual_review_count"] = statuses.count("MANUAL_REVIEW")
        evaluation["overall_status"] = (
            "NOT_ELIGIBLE" if "NOT_ELIGIBLE" in statuses else
            "MANUAL_REVIEW" if "MANUAL_REVIEW" in statuses else "ELIGIBLE")

        evaluation["security_report"] = security
        evaluation["ocr_engine"] = used_engine
        evaluation["ingestion_confidence"] = overall_confidence
        evaluation["bidder_text_snapshot"] = master_bidder_text
        evaluation["gfr_status"] = {"msme": msme_status, "startup": startup_status,
                                     "make_in_india": mii_status, "certifications": certifications,
                                     "exemptions_applied": len(gfr_exemptions)}
        return evaluation

    def run_full_pipeline(
        self,
        tender_bytes: bytes,
        tender_filename: str,
        bidders: Dict[str, bytes],
        bidder_filenames: Dict[str, str],
        api_key: str = None,
        progress_callback=None,
    ) -> dict:
        """
        Run the complete pipeline: tender → criteria → evaluate all bidders.

        Returns: {"criteria": list, "evaluations": dict}
        """
        # Process tender
        tender_result = self.process_tender(
            tender_bytes, tender_filename,
            api_key=api_key,
            progress_callback=progress_callback,
        )

        criteria = tender_result["criteria"]
        evaluations = {}

        # Evaluate each bidder
        for name, bidder_bytes_data in bidders.items():
            bidder_fname = bidder_filenames.get(name, f"{name}.txt")
            evaluation = self.evaluate_single_bidder(
                criteria, name, [bidder_bytes_data], [bidder_fname],
                api_key=api_key,
                progress_callback=progress_callback,
            )
            evaluations[name] = evaluation

        return {
            "criteria": criteria,
            "evaluations": evaluations,
            "tender_ocr_engine": tender_result["ocr_engine"],
        }
