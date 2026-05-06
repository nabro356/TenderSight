"""
TenderSight Orchestrator Agent — Manages the full evaluation pipeline.

Pipeline:
  1. Ingest tender document (smart OCR)
  2. Extract eligibility criteria
  3. For each bidder:
     a. Security scan
     b. Ingest bidder document (smart OCR)
     c. Combined evidence + evaluation (single LLM call)
     d. Reviewer pass (borderline verdicts only)
"""
import logging
from typing import Dict, List, Optional
from agents.base import BaseAgent, AgentInput, AgentOutput
from agents.ingestion_agent import ingest_document
from agents.security_agent import check_security
from agents.criteria_agent import extract_criteria
from agents.judge_agent import evaluate_bidder

logger = logging.getLogger(__name__)


class OrchestratorAgent(BaseAgent):
    """Manages the full TenderSight evaluation pipeline."""

    def __init__(self):
        super().__init__("OrchestratorAgent")

    async def execute(self, input_data: AgentInput) -> AgentOutput:
        """Not used directly — use run_pipeline instead."""
        return AgentOutput(status="success", result={})

    def process_tender(
        self,
        file_bytes: bytes,
        filename: str,
        api_key: str = None,
        progress_callback=None,
    ) -> dict:
        """
        Step 1: Ingest tender document and extract criteria.

        Returns: {"raw_text": str, "criteria": list, "ocr_engine": str}
        """
        if progress_callback:
            progress_callback("📄 Ingesting tender document...")

        # Smart ingestion (PyPDF → Gemini VLM → NVIDIA VLM)
        ingestion = ingest_document(
            file_bytes, filename,
            api_key=api_key,
            progress_callback=progress_callback,
        )

        if not ingestion["raw_text"] or ingestion["confidence"] == 0.0:
            raise ValueError(f"Could not extract text from tender document ({ingestion['ocr_engine']})")

        if progress_callback:
            progress_callback(f"📋 Tender text extracted ({ingestion['ocr_engine']}, {ingestion['confidence']:.0%} confidence)")

        # Extract criteria
        if progress_callback:
            progress_callback("🔍 Extracting eligibility criteria...")

        criteria = extract_criteria(
            ingestion["raw_text"],
            api_key=api_key,
            progress_callback=progress_callback,
        )

        return {
            "raw_text": ingestion["raw_text"],
            "criteria": criteria,
            "ocr_engine": ingestion["ocr_engine"],
            "confidence": ingestion["confidence"],
            "pages": ingestion.get("pages", 0),
        }

    def evaluate_single_bidder(
        self,
        criteria: list,
        bidder_name: str,
        bidder_bytes_list: List[bytes],
        bidder_filenames: List[str],
        api_key: str = None,
        progress_callback=None,
    ) -> dict:
        """
        Evaluate a single bidder: Security → Ingest → Evaluate.

        Returns: evaluation dict with verdicts.
        """
        # 1. Ingest bidder documents (smart OCR)
        if progress_callback:
            progress_callback(f"📄 Ingesting {bidder_name}'s documents...")

        master_bidder_text = ""
        overall_confidence = 0.0
        used_engine = "unknown"

        for b_bytes, b_fname in zip(bidder_bytes_list, bidder_filenames):
            ingestion = ingest_document(
                b_bytes, b_fname,
                api_key=api_key,
                progress_callback=progress_callback,
            )
            master_bidder_text += f"\n\n--- Document: {b_fname} ---\n\n{ingestion['raw_text']}"
            overall_confidence += ingestion["confidence"]
            used_engine = ingestion["ocr_engine"]
            
        if not master_bidder_text.strip():
            return {
                "bidder_name": bidder_name,
                "overall_status": "MANUAL_REVIEW",
                "verdicts": [],
                "eligible_count": 0,
                "not_eligible_count": 0,
                "manual_review_count": len(criteria),
                "error": "Could not extract text from any bidder documents",
                "ocr_engine": used_engine,
            }
            
        overall_confidence /= len(bidder_bytes_list) if bidder_bytes_list else 1

        # 2. Security scan
        if progress_callback:
            progress_callback(f"🛡️ Security scanning {bidder_name}...")

        security = check_security(master_bidder_text, filename="Multiple Documents")

        if not security.get("is_safe", True):
            return {
                "bidder_name": bidder_name,
                "overall_status": "NOT_ELIGIBLE",
                "verdicts": [],
                "eligible_count": 0,
                "not_eligible_count": len(criteria),
                "manual_review_count": 0,
                "error": f"Security threat detected: {security.get('threats', [])}",
                "security_report": security,
                "ocr_engine": used_engine,
            }

        # 3. Combined evaluation (single LLM call)
        if progress_callback:
            progress_callback(f"🧠 Evaluating {bidder_name}...")

        evaluation = evaluate_bidder(
            criteria, master_bidder_text, bidder_name,
            api_key=api_key,
            progress_callback=progress_callback,
        )

        evaluation["security_report"] = security
        evaluation["ocr_engine"] = used_engine
        evaluation["ingestion_confidence"] = overall_confidence
        evaluation["bidder_text_snapshot"] = master_bidder_text # Save for UI highlighting

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
                criteria, name, bidder_bytes_data, bidder_fname,
                api_key=api_key,
                progress_callback=progress_callback,
            )
            evaluations[name] = evaluation

        return {
            "criteria": criteria,
            "evaluations": evaluations,
            "tender_ocr_engine": tender_result["ocr_engine"],
        }
