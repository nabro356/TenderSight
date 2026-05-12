"""
Pydantic data models for TenderSight.
"""
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
from datetime import datetime


class CriterionType(str, Enum):
    FINANCIAL = "Financial"
    EXPERIENCE = "Experience"
    COMPLIANCE = "Compliance"
    TECHNICAL = "Technical"


class VerdictStatus(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    NOT_ELIGIBLE = "NOT_ELIGIBLE"
    MANUAL_REVIEW = "MANUAL_REVIEW"


class SubCondition(BaseModel):
    parameter: str
    operator: str
    threshold: str
    unit: str = ""


class Criterion(BaseModel):
    id: str
    text: str
    type: CriterionType
    mandatory: bool = True
    sub_conditions: list[SubCondition] = []
    source_section: str = ""


class EvidenceFragment(BaseModel):
    criterion_id: str
    value: str
    source_document: str
    source_section: str = ""
    confidence: float = 0.95
    extraction_method: str = "llm_extraction"
    raw_excerpt: str = ""


class Verdict(BaseModel):
    criterion_id: str
    criterion_text: str
    criterion_type: str
    bidder_name: str
    status: VerdictStatus
    confidence: float
    reasoning: str
    evidence_used: list[EvidenceFragment] = []
    review_reason: Optional[str] = None


class BidderEvaluation(BaseModel):
    bidder_name: str
    overall_status: VerdictStatus
    verdicts: list[Verdict] = []
    eligible_count: int = 0
    not_eligible_count: int = 0
    manual_review_count: int = 0
    evaluation_timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat()
    )


class TenderEvaluation(BaseModel):
    tender_title: str
    tender_ref: str
    criteria: list[Criterion] = []
    bidder_evaluations: list[BidderEvaluation] = []
    evaluation_timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat()
    )
