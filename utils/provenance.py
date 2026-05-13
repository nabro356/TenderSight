"""
Evidence Provenance DAG — TenderSight v3.0

Unlike a flat hash-chained audit log, this builds a Directed Acyclic Graph
of reasoning provenance. Every verdict traces back through:

    Verdict ← Reasoning ← Evidence ← Source (document, page, clause)

This lets a procurement officer walk from any verdict to the exact clause
that produced it, through every intermediate step.

Zero additional LLM calls — this is pure bookkeeping on data the agents
already produce.
"""
import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ─── Provenance Node Types ───

class ProvenanceNode:
    """A single node in the provenance DAG."""

    __slots__ = ("node_id", "node_type", "timestamp", "actor", "data", "parent_ids", "hash")

    def __init__(
        self,
        node_type: str,
        actor: str,
        data: dict,
        parent_ids: Optional[List[str]] = None,
    ):
        self.node_type = node_type
        self.actor = actor
        self.data = data
        self.parent_ids = parent_ids or []
        self.timestamp = datetime.now(timezone.utc).isoformat()
        # Deterministic node ID from content
        self.node_id = self._compute_id()
        self.hash = self._compute_hash()

    def _compute_id(self) -> str:
        """Deterministic ID from type + actor + timestamp."""
        raw = f"{self.node_type}:{self.actor}:{self.timestamp}:{json.dumps(self.data, sort_keys=True, default=str)}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def _compute_hash(self) -> str:
        """Full integrity hash including parent references."""
        raw = json.dumps({
            "node_id": self.node_id,
            "node_type": self.node_type,
            "actor": self.actor,
            "data": self.data,
            "parent_ids": self.parent_ids,
            "timestamp": self.timestamp,
        }, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "actor": self.actor,
            "timestamp": self.timestamp,
            "data": self.data,
            "parent_ids": self.parent_ids,
            "hash": self.hash,
        }


class ProvenanceDAG:
    """
    Directed Acyclic Graph of evidence provenance for a single tender evaluation.

    Usage:
        dag = ProvenanceDAG(tender_id="TND-ABC123")

        # Record document ingestion
        doc_node = dag.record_ingestion("rfp.pdf", "rfp", "pypdf", 0.95, 15200)

        # Record criteria extraction (linked to document)
        crit_node = dag.record_criteria_extraction(
            criteria=[...], source_doc_node=doc_node
        )

        # Record verdict (linked to evidence + criteria)
        verdict_node = dag.record_verdict(
            bidder="Bharat Corp", criterion_id="FIN-001",
            status="NOT_ELIGIBLE", confidence=0.95,
            evidence_value="Rs. 3.2 Cr", threshold="Rs. 5 Cr",
            source_page="Page 2, Para 3", source_clause="Clause 4.1.1",
            extraction_method="deterministic_engine",
            parent_nodes=[crit_node, evidence_node]
        )

        # Export full provenance chain
        trail = dag.get_verdict_ancestry(verdict_node.node_id)
    """

    def __init__(self, tender_id: str):
        self.tender_id = tender_id
        self.nodes: Dict[str, ProvenanceNode] = {}
        self.created_at = datetime.now(timezone.utc).isoformat()

    def _add_node(self, node: ProvenanceNode) -> ProvenanceNode:
        """Add a node to the DAG."""
        self.nodes[node.node_id] = node
        return node

    # ─── Recording Methods ───

    def record_bundle_upload(self, filenames: List[str], doc_types: Dict[str, str]) -> ProvenanceNode:
        """Record tender bundle upload."""
        return self._add_node(ProvenanceNode(
            node_type="BUNDLE_UPLOAD",
            actor="system",
            data={
                "tender_id": self.tender_id,
                "file_count": len(filenames),
                "files": [{"name": f, "type": doc_types.get(f, "unknown")} for f in filenames],
            },
        ))

    def record_ingestion(
        self, filename: str, doc_type: str, ocr_engine: str,
        confidence: float, char_count: int,
        parent_ids: Optional[List[str]] = None,
    ) -> ProvenanceNode:
        """Record a single document ingestion."""
        return self._add_node(ProvenanceNode(
            node_type="DOCUMENT_INGESTED",
            actor="ingestion_agent",
            data={
                "filename": filename,
                "doc_type": doc_type,
                "ocr_engine": ocr_engine,
                "confidence": confidence,
                "char_count": char_count,
            },
            parent_ids=parent_ids,
        ))

    def record_criteria_extraction(
        self, criteria_ids: List[str], source_doc: str,
        parent_ids: Optional[List[str]] = None,
    ) -> ProvenanceNode:
        """Record criteria extraction from a document."""
        return self._add_node(ProvenanceNode(
            node_type="CRITERIA_EXTRACTED",
            actor="criteria_agent",
            data={
                "criteria_count": len(criteria_ids),
                "criteria_ids": criteria_ids,
                "source_document": source_doc,
            },
            parent_ids=parent_ids,
        ))

    def record_conflict_detected(
        self, criterion_id: str, doc_a: str, doc_b: str,
        value_a: str, value_b: str, resolution: str,
        parent_ids: Optional[List[str]] = None,
    ) -> ProvenanceNode:
        """Record a cross-document conflict detection."""
        return self._add_node(ProvenanceNode(
            node_type="CONFLICT_DETECTED",
            actor="bundle_processor",
            data={
                "criterion_id": criterion_id,
                "doc_a": doc_a, "value_a": value_a,
                "doc_b": doc_b, "value_b": value_b,
                "resolution": resolution,
            },
            parent_ids=parent_ids,
        ))

    def record_security_scan(
        self, bidder_name: str, safe: bool, threats: List[str],
        parent_ids: Optional[List[str]] = None,
    ) -> ProvenanceNode:
        """Record security scan result."""
        return self._add_node(ProvenanceNode(
            node_type="SECURITY_SCAN",
            actor="security_agent",
            data={
                "bidder": bidder_name,
                "safe": safe,
                "threat_count": len(threats),
                "threats": threats[:3],  # Keep payload small
            },
            parent_ids=parent_ids,
        ))

    def record_deterministic_check(
        self, bidder_name: str, criterion_id: str,
        status: str, checks: List[dict],
        parent_ids: Optional[List[str]] = None,
    ) -> ProvenanceNode:
        """Record a deterministic engine resolution (zero LLM cost)."""
        return self._add_node(ProvenanceNode(
            node_type="DETERMINISTIC_CHECK",
            actor="deterministic_engine",
            data={
                "bidder": bidder_name,
                "criterion_id": criterion_id,
                "status": status,
                "checks": checks,
                "llm_cost": 0,
            },
            parent_ids=parent_ids,
        ))

    def record_llm_verdict(
        self, bidder_name: str, criterion_id: str,
        status: str, confidence: float,
        evidence_value: str, source_page: str,
        reasoning: str,
        parent_ids: Optional[List[str]] = None,
    ) -> ProvenanceNode:
        """Record an LLM-generated verdict."""
        return self._add_node(ProvenanceNode(
            node_type="LLM_VERDICT",
            actor="judge_agent",
            data={
                "bidder": bidder_name,
                "criterion_id": criterion_id,
                "status": status,
                "confidence": confidence,
                "evidence_value": evidence_value,
                "source_page": source_page,
                "reasoning_summary": reasoning[:200],
            },
            parent_ids=parent_ids,
        ))

    def record_gfr_exemption(
        self, bidder_name: str, criterion_id: str,
        exemption_type: str, certificate_ref: str,
        gfr_rule: str,
        parent_ids: Optional[List[str]] = None,
    ) -> ProvenanceNode:
        """Record a GFR 2017 rule-based exemption (zero LLM cost)."""
        return self._add_node(ProvenanceNode(
            node_type="GFR_EXEMPTION",
            actor="procurement_rules_engine",
            data={
                "bidder": bidder_name,
                "criterion_id": criterion_id,
                "exemption_type": exemption_type,
                "certificate_ref": certificate_ref,
                "gfr_rule": gfr_rule,
                "llm_cost": 0,
            },
            parent_ids=parent_ids,
        ))

    def record_human_override(
        self, operator: str, bidder_name: str, criterion_id: str,
        old_status: str, new_status: str, reason: str,
        parent_ids: Optional[List[str]] = None,
    ) -> ProvenanceNode:
        """Record a human operator override."""
        return self._add_node(ProvenanceNode(
            node_type="HUMAN_OVERRIDE",
            actor=f"operator:{operator}",
            data={
                "bidder": bidder_name,
                "criterion_id": criterion_id,
                "old_status": old_status,
                "new_status": new_status,
                "reason": reason,
            },
            parent_ids=parent_ids,
        ))

    def record_anomaly(
        self, bidder_name: str, z_score: float, reason: str,
        parent_ids: Optional[List[str]] = None,
    ) -> ProvenanceNode:
        """Record anomaly detection."""
        return self._add_node(ProvenanceNode(
            node_type="ANOMALY_DETECTED",
            actor="anomaly_detector",
            data={"bidder": bidder_name, "z_score": z_score, "reason": reason},
            parent_ids=parent_ids,
        ))

    def record_cartel_alert(
        self, bidder1: str, bidder2: str, shared_entity: str, link_type: str,
        parent_ids: Optional[List[str]] = None,
    ) -> ProvenanceNode:
        """Record cartel detection alert."""
        return self._add_node(ProvenanceNode(
            node_type="CARTEL_ALERT",
            actor="cartel_detector",
            data={
                "bidder1": bidder1, "bidder2": bidder2,
                "shared_entity": shared_entity, "link_type": link_type,
            },
            parent_ids=parent_ids,
        ))

    def record_report_export(self, format: str) -> ProvenanceNode:
        """Record report generation."""
        return self._add_node(ProvenanceNode(
            node_type="REPORT_EXPORTED",
            actor="report_generator",
            data={"format": format, "node_count": len(self.nodes)},
        ))

    # ─── Query Methods ───

    def get_verdict_ancestry(self, node_id: str) -> List[dict]:
        """
        Walk backward from a verdict node to all its ancestors.
        Returns the full provenance chain as a flat list.
        """
        visited = set()
        ancestry = []

        def _walk(nid: str):
            if nid in visited or nid not in self.nodes:
                return
            visited.add(nid)
            node = self.nodes[nid]
            ancestry.append(node.to_dict())
            for pid in node.parent_ids:
                _walk(pid)

        _walk(node_id)
        return ancestry

    def get_nodes_by_type(self, node_type: str) -> List[dict]:
        """Get all nodes of a specific type."""
        return [n.to_dict() for n in self.nodes.values() if n.node_type == node_type]

    def get_bidder_trail(self, bidder_name: str) -> List[dict]:
        """Get all provenance nodes related to a specific bidder."""
        result = []
        for node in self.nodes.values():
            if node.data.get("bidder") == bidder_name or \
               node.data.get("bidder1") == bidder_name or \
               node.data.get("bidder2") == bidder_name:
                result.append(node.to_dict())
        return sorted(result, key=lambda x: x["timestamp"])

    def verify_integrity(self) -> dict:
        """Verify that no node has been tampered with."""
        valid = 0
        invalid = 0
        broken_nodes = []
        for node in self.nodes.values():
            recomputed = node._compute_hash()
            if recomputed == node.hash:
                valid += 1
            else:
                invalid += 1
                broken_nodes.append(node.node_id)
        return {
            "total_nodes": len(self.nodes),
            "valid": valid,
            "invalid": invalid,
            "integrity": "PASS" if invalid == 0 else "FAIL",
            "broken_nodes": broken_nodes,
        }

    def export_full_trail(self) -> dict:
        """Export the entire DAG as a JSON-serializable dict."""
        return {
            "tender_id": self.tender_id,
            "created_at": self.created_at,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "node_count": len(self.nodes),
            "integrity": self.verify_integrity(),
            "nodes": [n.to_dict() for n in sorted(
                self.nodes.values(), key=lambda x: x.timestamp
            )],
        }


# ─── Global registry (one DAG per tender, lives in memory alongside evaluation) ───

_active_dags: Dict[str, ProvenanceDAG] = {}


def get_or_create_dag(tender_id: str) -> ProvenanceDAG:
    """Get or create a provenance DAG for a tender."""
    if tender_id not in _active_dags:
        _active_dags[tender_id] = ProvenanceDAG(tender_id)
    return _active_dags[tender_id]


def get_dag(tender_id: str) -> Optional[ProvenanceDAG]:
    """Get an existing DAG (returns None if not found)."""
    return _active_dags.get(tender_id)
