"""
Deterministic Rule Engine + Procurement Rules Engine — TenderSight v3.0

Pass 1 of the evaluation protocol. Executes programmatic comparisons
for numeric criteria AND applies GFR 2017 / GeM compliance rules
deterministically — bypassing the LLM entirely for clear-cut cases.

New in v3.0:
  - GFR 2017 MSME/Startup exemption engine (Rule 170(i), 173(i))
  - GeM metadata regex extraction (bid number, category, amounts)
  - Make in India classification (PP-MII Order 2017)
  - Document hierarchy awareness (Corrigendum > ATC > RFP)

Every rule resolved here = one fewer LLM call = lower cost + higher reliability.
"""
import re
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# SECTION 1: Indian Currency & Numeric Parsing (unchanged)
# ═══════════════════════════════════════════════════════════

def parse_inr_amount(text: str) -> Optional[float]:
    """
    Parse Indian Rupee amounts from text.
    Handles: Rs. 5,00,00,000  |  Rs.5 Crore  |  5,500,000  |  Rs. 8,20,66,667
    Returns amount in Rupees (not Crore/Lakh).
    """
    if text is None:
        return None
    text = str(text).strip()
    if not text:
        return None

    crore_match = re.search(
        r"(?:Rs\.?\s*)?([\d]+(?:\.\d+)?)\s*(?:Crore|Cr)\b", text, re.IGNORECASE
    )
    if crore_match:
        return float(crore_match.group(1)) * 1_00_00_000

    lakh_match = re.search(
        r"(?:Rs\.?\s*)?([\d]+(?:\.\d+)?)\s*(?:Lakh|Lac)\b", text, re.IGNORECASE
    )
    if lakh_match:
        return float(lakh_match.group(1)) * 1_00_000

    num_match = re.search(r"(?:Rs\.?\s*/?\\-?\s*)?(\d[\d,]+\d)", text)
    if num_match:
        num_str = num_match.group(1).replace(",", "")
        try:
            return float(num_str)
        except ValueError:
            pass

    plain_match = re.search(r"(\d+(?:\.\d+)?)", text)
    if plain_match:
        try:
            return float(plain_match.group(1))
        except ValueError:
            pass

    return None


def parse_integer(text: str) -> Optional[int]:
    """Extract an integer from text."""
    if text is None:
        return None
    text = str(text)
    match = re.search(r"(\d+)", text)
    if match:
        return int(match.group(1))
    return None


# ═══════════════════════════════════════════════════════════
# SECTION 2: Deterministic Evaluation (original, preserved)
# ═══════════════════════════════════════════════════════════

def evaluate_criterion_deterministic(
    criterion: dict, evidence: list, min_confidence: float = 0.90,
) -> Dict:
    """
    Attempt deterministic evaluation of a criterion based on sub-conditions.
    Returns: {"resolved": bool, "status": str, "confidence": float, ...}
    """
    sub_conditions = criterion.get("sub_conditions", [])
    if not sub_conditions:
        return _needs_llm("No sub-conditions defined for deterministic check")

    relevant_evidence = [e for e in evidence if e.get("criterion_id") == criterion.get("id")]
    if not relevant_evidence:
        return _needs_llm("No evidence found for this criterion")

    for ev in relevant_evidence:
        if ev.get("confidence", 0) < min_confidence:
            return _needs_llm(f"Evidence confidence ({ev.get('confidence', 0):.0%}) below threshold")

    checks = []
    all_pass = True
    any_fail = False

    for sc in sub_conditions:
        check_result = _check_sub_condition(sc, relevant_evidence)
        checks.append(check_result)
        if check_result["result"] == "FAIL":
            any_fail = True
            all_pass = False
        elif check_result["result"] == "UNKNOWN":
            all_pass = False

    if any_fail:
        return {"resolved": True, "status": "NOT_ELIGIBLE", "confidence": 0.95,
                "reasoning": " | ".join(f"{c['parameter']} -> {c['result']} ({c['detail']})" for c in checks),
                "checks_performed": checks}
    elif all_pass:
        return {"resolved": True, "status": "ELIGIBLE", "confidence": 0.95,
                "reasoning": " | ".join(f"{c['parameter']} -> {c['result']} ({c['detail']})" for c in checks),
                "checks_performed": checks}
    else:
        return _needs_llm("Some sub-conditions unresolvable: " + ", ".join(
            c["parameter"] for c in checks if c["result"] == "UNKNOWN"))


def _check_sub_condition(sc: dict, evidence: list) -> Dict:
    """Check a single sub-condition against evidence."""
    param = str(sc.get("parameter") or "")
    operator = str(sc.get("operator") or "")
    threshold_str = str(sc.get("threshold") or "")
    all_values = " | ".join(str(e.get("value", "")) + " " + str(e.get("raw_excerpt", "")) for e in evidence)

    if operator in (">=", "<=", "==", ">", "<"):
        threshold_val = parse_inr_amount(threshold_str) or parse_integer(threshold_str)
        if threshold_val is None:
            return _unknown_check(param, f"Cannot parse threshold: '{threshold_str}'")
        evidence_val = None
        for ev in evidence:
            val = parse_inr_amount(str(ev.get("value", "")))
            if val is None:
                val = parse_integer(str(ev.get("value", "")))
            if val is not None:
                evidence_val = val
                break
        if evidence_val is None:
            return _unknown_check(param, f"Cannot parse evidence value for {param}")
        if operator == ">=" and evidence_val >= threshold_val:
            return _pass_check(param, f"{evidence_val:,.0f} >= {threshold_val:,.0f}")
        elif operator == ">=" and evidence_val < threshold_val:
            if evidence_val >= threshold_val * 0.90:
                return _unknown_check(param, f"{evidence_val:,.0f} within 10% of {threshold_val:,.0f} (borderline)")
            return _fail_check(param, f"{evidence_val:,.0f} < {threshold_val:,.0f}")
        elif operator == "<=" and evidence_val <= threshold_val:
            return _pass_check(param, f"{evidence_val:,.0f} <= {threshold_val:,.0f}")
        elif operator == "==" and evidence_val == threshold_val:
            return _pass_check(param, f"{evidence_val:,.0f} == {threshold_val:,.0f}")
        elif operator in (">", "<"):
            if (operator == ">" and evidence_val > threshold_val) or (operator == "<" and evidence_val < threshold_val):
                return _pass_check(param, f"{evidence_val:,.0f} {operator} {threshold_val:,.0f}")
            return _fail_check(param, f"{evidence_val:,.0f} not {operator} {threshold_val:,.0f}")
        else:
            return _fail_check(param, f"{evidence_val:,.0f} does not satisfy {operator} {threshold_val:,.0f}")

    if operator == "exists":
        search_terms = threshold_str.lower().split()
        found = any(term in all_values.lower() for term in search_terms if len(term) > 3)
        if found:
            return _pass_check(param, f"'{threshold_str}' found in evidence")
        return _unknown_check(param, f"Cannot confirm '{threshold_str}' exists")

    if operator == "includes":
        if threshold_str.lower() in all_values.lower():
            return _pass_check(param, f"'{threshold_str}' found in scope")
        return _unknown_check(param, f"Cannot confirm scope includes '{threshold_str}'")

    return _unknown_check(param, f"Operator '{operator}' not handled deterministically")


def _pass_check(param, detail):
    return {"parameter": param, "result": "PASS", "detail": detail}

def _fail_check(param, detail):
    return {"parameter": param, "result": "FAIL", "detail": detail}

def _unknown_check(param, detail):
    return {"parameter": param, "result": "UNKNOWN", "detail": detail}

def _needs_llm(reason):
    return {"resolved": False, "status": "NEEDS_LLM", "confidence": 0.0,
            "reasoning": reason, "checks_performed": []}


# ═══════════════════════════════════════════════════════════
# SECTION 3: GFR 2017 Procurement Rules Engine (NEW in v3.0)
# ═══════════════════════════════════════════════════════════

_UDYAM_PATTERN = re.compile(r"(UDYAM[-\s]?[A-Z]{2}[-\s]?\d{2}[-\s]?\d{7})", re.IGNORECASE)
_DPIIT_PATTERN = re.compile(r"(DIPP\d+|DPIIT\d+|RECOGNITION\s*(?:NO|NUMBER)[.:]\s*\w+)", re.IGNORECASE)
_STARTUP_PATTERN = re.compile(r"(startup\s*india|dpiit\s*recogni[sz]ed|startup\s*certificate)", re.IGNORECASE)
_MSME_PATTERN = re.compile(r"(msme|micro\s*small\s*medium|udyam\s*registration|msmed?\s*act)", re.IGNORECASE)
_ISO_PATTERN = re.compile(r"(ISO\s*\d{4,5}(?:[-:]\d{4})?)", re.IGNORECASE)
_BIS_PATTERN = re.compile(r"(IS\s*\d{3,5}(?:[-:]\d{4})?|BIS\s*(?:license|cert|registration))", re.IGNORECASE)
_MAKE_IN_INDIA_PATTERN = re.compile(r"(make\s*in\s*india|domestic\s*(?:content|value)\s*(?:addition)?|local\s*content)", re.IGNORECASE)

EXEMPTABLE_CRITERIA_TYPES = {"Financial", "Experience"}
EXEMPTABLE_KEYWORDS = {"turnover", "annual turnover", "experience", "past performance",
                        "similar work", "emd", "earnest money", "bid security"}


class ProcurementRulesEngine:
    """GFR 2017 + GeM compliance rules. Deterministic. Auditable. Zero LLM cost."""

    @staticmethod
    def detect_msme_status(bidder_text: str) -> Dict:
        """Detect MSME/Udyam registration. GFR 2017 Rule 170(i)."""
        udyam_match = _UDYAM_PATTERN.search(bidder_text)
        msme_mentioned = _MSME_PATTERN.search(bidder_text)
        if udyam_match:
            return {"is_msme": True, "certificate_ref": udyam_match.group(1).strip(),
                    "confidence": 0.95, "gfr_rule": "Rule 170(i) -- MSE EMD Exemption; PP-MSE Policy"}
        elif msme_mentioned:
            return {"is_msme": True, "certificate_ref": "MSME mentioned (Udyam not extracted)",
                    "confidence": 0.70, "gfr_rule": "Rule 170(i) -- MSE EMD Exemption"}
        return {"is_msme": False, "certificate_ref": None, "confidence": 0.0, "gfr_rule": None}

    @staticmethod
    def detect_startup_status(bidder_text: str) -> Dict:
        """Detect DPIIT Startup India recognition. GFR 2017 Rule 173(i)."""
        dpiit_match = _DPIIT_PATTERN.search(bidder_text)
        startup_mentioned = _STARTUP_PATTERN.search(bidder_text)
        if dpiit_match:
            return {"is_startup": True, "certificate_ref": dpiit_match.group(1).strip(),
                    "confidence": 0.95, "gfr_rule": "Rule 173(i) -- Startup Relaxation"}
        elif startup_mentioned:
            return {"is_startup": True, "certificate_ref": "Startup mentioned (DPIIT not extracted)",
                    "confidence": 0.65, "gfr_rule": "Rule 173(i) -- Startup Relaxation"}
        return {"is_startup": False, "certificate_ref": None, "confidence": 0.0, "gfr_rule": None}

    @staticmethod
    def detect_make_in_india(bidder_text: str) -> Dict:
        """Detect Make in India / local content. PP-MII Order 2017."""
        mii_match = _MAKE_IN_INDIA_PATTERN.search(bidder_text)
        lc_match = re.search(r"local\s*content[:\s]*(\d+)\s*%", bidder_text, re.IGNORECASE)
        local_pct = int(lc_match.group(1)) if lc_match else None
        classification = "Non-Local"
        if local_pct is not None:
            if local_pct >= 50:
                classification = "Class-I Local Supplier"
            elif local_pct >= 20:
                classification = "Class-II Local Supplier"
        return {"make_in_india_mentioned": bool(mii_match), "local_content_pct": local_pct,
                "classification": classification,
                "purchase_preference": classification in ("Class-I Local Supplier", "Class-II Local Supplier")}

    @staticmethod
    def check_exemptions_for_criterion(criterion: dict, msme_status: dict, startup_status: dict) -> Optional[Dict]:
        """Check if a criterion is exempted by MSME/Startup policy. Returns exemption dict or None."""
        crit_type = str(criterion.get("type", "")).strip()
        crit_text = str(criterion.get("text", "")).lower()
        is_exemptable = crit_type in EXEMPTABLE_CRITERIA_TYPES or any(kw in crit_text for kw in EXEMPTABLE_KEYWORDS)
        if not is_exemptable:
            return None

        if msme_status.get("is_msme") and msme_status.get("confidence", 0) >= 0.70:
            if any(kw in crit_text for kw in ["emd", "earnest money", "bid security"]):
                return {"exempt": True, "status": "ELIGIBLE", "confidence": msme_status["confidence"],
                        "reasoning": f"Exempt under GFR 2017 {msme_status['gfr_rule']}. Cert: {msme_status['certificate_ref']}.",
                        "exemption_type": "MSME_EMD", "gfr_rule": msme_status["gfr_rule"],
                        "certificate_ref": msme_status["certificate_ref"]}
            if any(kw in crit_text for kw in ["turnover", "annual turnover", "experience", "past performance", "similar work"]):
                return {"exempt": True, "status": "ELIGIBLE", "confidence": msme_status["confidence"],
                        "reasoning": f"Exempt under PP-MSE Policy (turnover/experience relaxation). Cert: {msme_status['certificate_ref']}.",
                        "exemption_type": "MSME_TURNOVER_EXPERIENCE", "gfr_rule": msme_status["gfr_rule"],
                        "certificate_ref": msme_status["certificate_ref"]}

        if startup_status.get("is_startup") and startup_status.get("confidence", 0) >= 0.65:
            if any(kw in crit_text for kw in ["turnover", "annual turnover", "experience", "past performance",
                                                "similar work", "emd", "earnest money", "bid security"]):
                return {"exempt": True, "status": "ELIGIBLE", "confidence": startup_status["confidence"],
                        "reasoning": f"Exempt under GFR 2017 {startup_status['gfr_rule']}. Cert: {startup_status['certificate_ref']}.",
                        "exemption_type": "STARTUP_RELAXATION", "gfr_rule": startup_status["gfr_rule"],
                        "certificate_ref": startup_status["certificate_ref"]}
        return None


# ═══════════════════════════════════════════════════════════
# SECTION 4: GeM Metadata Extraction (NEW in v3.0)
# ═══════════════════════════════════════════════════════════

_GEM_BID_PATTERN = re.compile(r"(GEM\s*/\s*\d{4}\s*/\s*B\s*/\s*\d{5,9})", re.IGNORECASE)
_TENDER_REF_PATTERN = re.compile(r"(?:tender|bid|nit|rfp)\s*(?:no|number|ref|reference)[.:\s]*([A-Z0-9/\-]{6,40})", re.IGNORECASE)
_EMD_AMOUNT_PATTERN = re.compile(r"(?:emd|earnest\s*money|bid\s*security)\s*[:\-]?\s*(?:Rs\.?\s*)?([0-9,]+(?:\.\d+)?(?:\s*(?:Crore|Cr|Lakh|Lac))?)", re.IGNORECASE)
_ESTIMATED_COST_PATTERN = re.compile(r"(?:estimated\s*(?:cost|value)|tender\s*value|approximate\s*cost)\s*[:\-]?\s*(?:Rs\.?\s*)?([0-9,]+(?:\.\d+)?(?:\s*(?:Crore|Cr|Lakh|Lac))?)", re.IGNORECASE)


def extract_gem_metadata(tender_text: str) -> Dict:
    """Extract GeM / procurement metadata from tender text. Pure regex -- zero LLM cost."""
    result = {"gem_bid_number": None, "tender_reference": None, "estimated_cost": None,
              "estimated_cost_numeric": None, "emd_amount": None, "emd_amount_numeric": None,
              "is_gem_tender": False, "platform_detected": "unknown"}

    gem_bid = _GEM_BID_PATTERN.search(tender_text)
    if gem_bid:
        result["gem_bid_number"] = gem_bid.group(1).strip()
        result["is_gem_tender"] = True
        result["platform_detected"] = "GeM"

    ref_match = _TENDER_REF_PATTERN.search(tender_text)
    if ref_match:
        result["tender_reference"] = ref_match.group(1).strip()

    cost_match = _ESTIMATED_COST_PATTERN.search(tender_text)
    if cost_match:
        raw = cost_match.group(1).strip()
        result["estimated_cost"] = f"Rs. {raw}"
        result["estimated_cost_numeric"] = parse_inr_amount(raw)

    emd_match = _EMD_AMOUNT_PATTERN.search(tender_text)
    if emd_match:
        raw = emd_match.group(1).strip()
        result["emd_amount"] = f"Rs. {raw}"
        result["emd_amount_numeric"] = parse_inr_amount(raw)

    if not result["is_gem_tender"]:
        text_lower = tender_text.lower()
        if "gem.gov.in" in text_lower or "government e-marketplace" in text_lower:
            result["is_gem_tender"] = True
            result["platform_detected"] = "GeM"
        elif "cppp" in text_lower or "eprocure.gov.in" in text_lower:
            result["platform_detected"] = "CPPP"

    return result


def extract_certifications(text: str) -> List[Dict]:
    """Extract all certifications mentioned in text. Zero LLM cost."""
    certs = []
    for m in _ISO_PATTERN.finditer(text):
        certs.append({"type": "ISO", "reference": m.group(1).strip()})
    for m in _BIS_PATTERN.finditer(text):
        certs.append({"type": "BIS", "reference": m.group(1).strip()})
    for m in _UDYAM_PATTERN.finditer(text):
        certs.append({"type": "Udyam/MSME", "reference": m.group(1).strip()})
    for m in _DPIIT_PATTERN.finditer(text):
        certs.append({"type": "DPIIT/Startup", "reference": m.group(1).strip()})
    return certs
