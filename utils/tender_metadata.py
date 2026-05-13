"""
Utility helpers for lightweight tender metadata extraction.

These heuristics are intentionally conservative. They give the UI enough
structured context for briefing cards and operator surfaces without making
strong claims when the source text is unclear.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional


_DATE_PATTERNS = [
    r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
    r"\b\d{1,2}\s+[A-Za-z]{3,9}\s+\d{2,4}\b",
    r"\b[A-Za-z]{3,9}\s+\d{1,2},\s+\d{4}\b",
]

_AUTHORITY_HINTS = (
    "ministry",
    "department",
    "directorate",
    "authority",
    "corporation",
    "office of",
    "government",
    "force",
    "railway",
    "army",
    "navy",
    "police",
)


def _clean_match(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    value = re.sub(r"\s+", " ", str(value)).strip(" :-\n\t")
    return value or None


def _find_amount_near_label(text: str, labels: List[str]) -> Optional[str]:
    amount_pattern = (
        r"(Rs\.?\s*[\d,]+(?:\.\d+)?(?:\s*(?:Crore|Cr|Lakh|Lakhs|Lac))?"
        r"|INR\s*[\d,]+(?:\.\d+)?(?:\s*(?:Crore|Cr|Lakh|Lakhs|Lac))?"
        r"|₹\s*[\d,]+(?:\.\d+)?(?:\s*(?:Crore|Cr|Lakh|Lakhs|Lac))?)"
    )
    for label in labels:
        regex = rf"(?is){label}.{{0,80}}?{amount_pattern}"
        match = re.search(regex, text)
        if match:
            return _clean_match(match.group(1))
    return None


def _find_date_near_label(text: str, labels: List[str]) -> Optional[str]:
    date_pattern = "|".join(_DATE_PATTERNS)
    for label in labels:
        regex = rf"(?is){label}.{{0,80}}?({date_pattern}(?:\s+\d{{1,2}}:\d{{2}}(?:\s*[APMapm]{{2}})?(?:\s*IST)?)?)"
        match = re.search(regex, text)
        if match:
            return _clean_match(match.group(1))
    return None


def _find_portal(text: str) -> Optional[str]:
    portal_patterns = [
        r"\b(?:gem\.gov\.in|bidplus\.gem\.gov\.in)\b",
        r"\b(?:defproc\.gov\.in)\b",
        r"\b(?:eprocure(?:ment)?\.[^\s/]+)\b",
        r"\b(?:tenderwizard\.[^\s/]+)\b",
        r"\b(?:cppp|central public procurement portal)\b",
    ]
    for pattern in portal_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return _clean_match(match.group(0))
    return None


def _find_authority(text: str) -> Optional[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines[:60]:
        lowered = line.lower()
        if any(hint in lowered for hint in _AUTHORITY_HINTS) and 6 <= len(line) <= 120:
            return _clean_match(line)

    regexes = [
        r"(?i)(?:issued by|authority|procuring entity|buyer name|department|organisation|organization)\s*[:\-]\s*([^\n]+)",
        r"(?i)(?:office of)\s+([^\n]+)",
    ]
    for regex in regexes:
        match = re.search(regex, text)
        if match:
            return _clean_match(match.group(1))
    return None


def extract_tender_metadata(raw_text: str, filenames: Optional[List[str]] = None) -> Dict[str, Optional[str]]:
    """Extract lightweight tender metadata from combined tender text."""
    text = raw_text or ""
    filenames = filenames or []

    authority = _find_authority(text)
    closing_date = _find_date_near_label(
        text,
        [
            r"closing date",
            r"last date(?: and time)?",
            r"bid submission end date",
            r"submission deadline",
            r"date of closing",
            r"tender closing",
        ],
    )
    pre_bid_date = _find_date_near_label(
        text,
        [
            r"pre[-\s]?bid(?: meeting)?",
            r"pre[-\s]?bid date",
            r"clarification meeting",
        ],
    )
    emd_amount = _find_amount_near_label(text, [r"emd", r"earnest money(?: deposit)?"])
    estimated_value = _find_amount_near_label(
        text,
        [
            r"estimated cost",
            r"tender value",
            r"value of work",
            r"estimated value",
            r"project cost",
            r"bid value",
        ],
    )
    portal = _find_portal(text)

    return {
        "title": _clean_match(filenames[0]) if filenames else "Tender Bundle",
        "authority": authority,
        "closing_date": closing_date,
        "pre_bid_date": pre_bid_date,
        "emd_amount": emd_amount,
        "estimated_value": estimated_value,
        "portal": portal,
        "bundle_count": str(len(filenames)) if filenames else None,
    }
