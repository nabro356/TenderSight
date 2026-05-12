"""
Deterministic Rule Engine — Pass 1 of the 3-Pass Evaluation Protocol.

Executes programmatic comparisons for numeric criteria where extraction
confidence is high, bypassing the LLM entirely for clear-cut cases.
"""
import re
import logging
from typing import Dict, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


# ─── Indian Currency Parser ───

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

    # Pattern 1: "X Crore" or "X.Y Cr"
    crore_match = re.search(
        r"(?:Rs\.?\s*)?(\d+(?:\.\d+)?)\s*(?:Crore|Cr)\b", text, re.IGNORECASE
    )
    if crore_match:
        return float(crore_match.group(1)) * 1_00_00_000

    # Pattern 2: "X Lakh" or "X.Y Lakh"
    lakh_match = re.search(
        r"(?:Rs\.?\s*)?(\d+(?:\.\d+)?)\s*(?:Lakh|Lac)\b", text, re.IGNORECASE
    )
    if lakh_match:
        return float(lakh_match.group(1)) * 1_00_000

    # Pattern 3: Indian-format number "Rs.8,20,66,667" or "5,00,00,000"
    # Indian system: rightmost 3 digits, then groups of 2
    num_match = re.search(
        r"(?:Rs\.?\s*/?\-?\s*)?(\d[\d,]+\d)", text
    )
    if num_match:
        num_str = num_match.group(1).replace(",", "")
        try:
            return float(num_str)
        except ValueError:
            pass

    # Pattern 4: Plain number
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
    if not text:
        return None
    match = re.search(r"(\d+)", text)
    if match:
        return int(match.group(1))
    return None


# ─── Deterministic Evaluation ───

def evaluate_criterion_deterministic(
    criterion: dict,
    evidence: list,
    min_confidence: float = 0.90,
) -> Dict:
    """
    Attempt deterministic evaluation of a criterion based on sub-conditions.

    Returns:
        {
            "resolved": bool,        # True if deterministic check succeeded
            "status": str,           # "ELIGIBLE" | "NOT_ELIGIBLE" | "NEEDS_LLM"
            "confidence": float,
            "reasoning": str,
            "checks_performed": list[dict],
        }
    """
    sub_conditions = criterion.get("sub_conditions", [])
    if not sub_conditions:
        return _needs_llm("No sub-conditions defined for deterministic check")

    relevant_evidence = [
        e for e in evidence
        if e.get("criterion_id") == criterion.get("id")
    ]

    if not relevant_evidence:
        return _needs_llm("No evidence found for this criterion")

    # Check if evidence confidence is high enough for deterministic evaluation
    for ev in relevant_evidence:
        if ev.get("confidence", 0) < min_confidence:
            return _needs_llm(
                f"Evidence confidence ({ev.get('confidence', 0):.0%}) "
                f"below threshold ({min_confidence:.0%}) — deferring to LLM"
            )

    checks = []
    all_pass = True
    any_fail = False

    for sc in sub_conditions:
        param = sc.get("parameter", "")
        operator = sc.get("operator", "")
        threshold = sc.get("threshold", "")

        # Try to resolve this sub-condition
        check_result = _check_sub_condition(sc, relevant_evidence)
        checks.append(check_result)

        if check_result["result"] == "FAIL":
            any_fail = True
            all_pass = False
        elif check_result["result"] == "UNKNOWN":
            all_pass = False

    # Determine overall result
    if any_fail:
        reasoning_parts = [
            f"Pass 1 deterministic check: {c['parameter']} → {c['result']} ({c['detail']})"
            for c in checks
        ]
        return {
            "resolved": True,
            "status": "NOT_ELIGIBLE",
            "confidence": 0.95,
            "reasoning": " | ".join(reasoning_parts),
            "checks_performed": checks,
        }
    elif all_pass:
        reasoning_parts = [
            f"Pass 1 deterministic check: {c['parameter']} → {c['result']} ({c['detail']})"
            for c in checks
        ]
        return {
            "resolved": True,
            "status": "ELIGIBLE",
            "confidence": 0.95,
            "reasoning": " | ".join(reasoning_parts),
            "checks_performed": checks,
        }
    else:
        return _needs_llm(
            "Some sub-conditions could not be resolved deterministically: "
            + ", ".join(c["parameter"] for c in checks if c["result"] == "UNKNOWN")
        )


def _check_sub_condition(sc: dict, evidence: list) -> Dict:
    """Check a single sub-condition against evidence."""
    param = str(sc.get("parameter") or "")
    operator = str(sc.get("operator") or "")
    threshold_str = str(sc.get("threshold") or "")

    # Combine all evidence text for searching
    all_values = " | ".join(
        str(e.get("value", "")) + " " + str(e.get("raw_excerpt", ""))
        for e in evidence
    )

    # ─── Numeric comparisons (>=, <=, ==) ───
    if operator in (">=", "<=", "==", ">", "<"):
        threshold_val = parse_inr_amount(threshold_str) or parse_integer(threshold_str)
        if threshold_val is None:
            return _unknown_check(param, f"Cannot parse threshold: '{threshold_str}'")

        # Extract the bidder's value from evidence
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

        # Compare
        if operator == ">=" and evidence_val >= threshold_val:
            return _pass_check(param, f"{evidence_val:,.0f} >= {threshold_val:,.0f}")
        elif operator == ">=" and evidence_val < threshold_val:
            # Check if borderline (within 10%)
            if evidence_val >= threshold_val * 0.90:
                return _unknown_check(
                    param,
                    f"{evidence_val:,.0f} is within 10% of {threshold_val:,.0f} (borderline)"
                )
            return _fail_check(param, f"{evidence_val:,.0f} < {threshold_val:,.0f}")
        elif operator == "<=" and evidence_val <= threshold_val:
            return _pass_check(param, f"{evidence_val:,.0f} <= {threshold_val:,.0f}")
        elif operator == "==" and evidence_val == threshold_val:
            return _pass_check(param, f"{evidence_val:,.0f} == {threshold_val:,.0f}")
        elif operator in (">", "<"):
            if (operator == ">" and evidence_val > threshold_val) or \
               (operator == "<" and evidence_val < threshold_val):
                return _pass_check(param, f"{evidence_val:,.0f} {operator} {threshold_val:,.0f}")
            return _fail_check(param, f"{evidence_val:,.0f} not {operator} {threshold_val:,.0f}")
        else:
            return _fail_check(param, f"{evidence_val:,.0f} does not satisfy {operator} {threshold_val:,.0f}")

    # ─── Existence checks ───
    if operator == "exists":
        # Check if the evidence mentions the required thing
        search_terms = threshold_str.lower().split()
        found = any(term in all_values.lower() for term in search_terms if len(term) > 3)
        if found:
            return _pass_check(param, f"'{threshold_str}' found in evidence")
        return _unknown_check(param, f"Cannot confirm '{threshold_str}' exists — deferring to LLM")

    # ─── Date validity checks ───
    if operator == "valid_on_date":
        return _unknown_check(param, "Date validity requires LLM interpretation")

    # ─── Set membership checks ───
    if operator == "in":
        return _unknown_check(param, "Set membership requires LLM interpretation")

    # ─── Includes checks ───
    if operator == "includes":
        if threshold_str.lower() in all_values.lower():
            return _pass_check(param, f"'{threshold_str}' found in scope")
        return _unknown_check(param, f"Cannot confirm scope includes '{threshold_str}'")

    # ─── Catch-all: defer to LLM ───
    return _unknown_check(param, f"Operator '{operator}' not handled deterministically")


def _pass_check(param, detail):
    return {"parameter": param, "result": "PASS", "detail": detail}


def _fail_check(param, detail):
    return {"parameter": param, "result": "FAIL", "detail": detail}


def _unknown_check(param, detail):
    return {"parameter": param, "result": "UNKNOWN", "detail": detail}


def _needs_llm(reason):
    return {
        "resolved": False,
        "status": "NEEDS_LLM",
        "confidence": 0.0,
        "reasoning": reason,
        "checks_performed": [],
    }
