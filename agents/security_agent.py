"""
Security Agent — Detects prompt injection and sanitizes bidder submissions.

Checks for:
- Prompt injection patterns in text content
- Adversarial instructions embedded in documents
- Anomalous Unicode characters
"""
import re
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

# Known prompt injection patterns
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"ignore\s+(all\s+)?above\s+instructions",
    r"disregard\s+(all\s+)?previous",
    r"forget\s+(all\s+)?previous",
    r"override\s+.*(evaluation|verdict|status|result)",
    r"mark\s+(this\s+)?(bidder\s+)?as\s+(eligible|pass|approved)",
    r"output\s+(only\s+)?(pass|eligible|approved)",
    r"you\s+are\s+now\s+a",
    r"new\s+instructions?\s*:",
    r"system\s*:\s*you",
    r"<\s*system\s*>",
    r"act\s+as\s+(if|though)",
    r"pretend\s+(you\s+are|to\s+be)",
]

# Anomalous Unicode ranges (zero-width, bidirectional overrides, etc.)
ANOMALOUS_UNICODE = re.compile(
    r"[\u200b-\u200f\u202a-\u202e\u2060-\u2064\ufeff\u00ad]"
)


def check_security(text: str, filename: str = "") -> Dict:
    """
    Run security checks on document text.

    Returns:
        {
            "safe": bool,
            "threats_detected": list[str],
            "sanitized_text": str,
            "anomalous_chars_removed": int,
        }
    """
    threats: List[str] = []

    # 1. Check filename for injection
    if filename:
        for pattern in INJECTION_PATTERNS[:3]:  # Quick check on filename
            if re.search(pattern, filename, re.IGNORECASE):
                threats.append(f"Prompt injection detected in filename: '{filename}'")
                break

    # 2. Check document body for injection patterns
    text_lower = text.lower()
    for pattern in INJECTION_PATTERNS:
        matches = re.findall(pattern, text_lower)
        if matches:
            # Find the actual line containing the injection
            for line in text.split("\n"):
                if re.search(pattern, line, re.IGNORECASE):
                    threats.append(
                        f"Prompt injection pattern detected: '{line.strip()[:100]}'"
                    )
                    break

    # 3. Strip anomalous Unicode
    anomalous_matches = ANOMALOUS_UNICODE.findall(text)
    anomalous_count = len(anomalous_matches)
    sanitized = ANOMALOUS_UNICODE.sub("", text)

    if anomalous_count > 0:
        threats.append(
            f"Removed {anomalous_count} anomalous Unicode characters "
            f"(zero-width, bidirectional overrides)"
        )

    # 4. Check for excessive hidden content indicators
    visible_len = len(sanitized.strip())
    if visible_len > 0:
        # Check for suspiciously high whitespace ratio
        whitespace_ratio = sanitized.count(" ") / visible_len
        if whitespace_ratio > 0.7:
            threats.append("Suspiciously high whitespace ratio (possible hidden content)")

    is_safe = len([t for t in threats if "injection" in t.lower()]) == 0

    if threats:
        logger.warning("Security threats detected: %s", threats)

    return {
        "safe": is_safe,
        "threats_detected": threats,
        "sanitized_text": sanitized,
        "anomalous_chars_removed": anomalous_count,
    }
