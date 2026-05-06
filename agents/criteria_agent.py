"""
Criteria Extraction Agent — Extracts eligibility criteria from tender documents.
"""
import json
import logging
from langchain_core.messages import SystemMessage, HumanMessage
from utils.llm_utils import try_invoke_with_fallback

logger = logging.getLogger(__name__)


CRITERIA_EXTRACTION_PROMPT = """You are an expert in Indian government procurement and tender analysis.
You work for CRPF (Central Reserve Police Force) evaluating tender documents under GFR 2017 rules.

Given a tender document, extract ALL eligibility criteria as a structured JSON array.

For each criterion, provide:
- "id": A short ID like FIN-001, EXP-001, COMP-001, TECH-001
- "text": The full criterion text as stated in the tender
- "type": One of "Financial", "Experience", "Compliance", "Technical"
- "mandatory": true if the criterion uses words like "must", "shall", "mandatory"
- "sub_conditions": Array of specific measurable conditions, each with:
    - "parameter": What is being measured
    - "operator": Comparison operator (>=, <=, ==, exists, valid_on_date)
    - "threshold": The required value
    - "unit": Unit of measurement
- "source_section": The section number from the tender (e.g., "4.1.1")

IMPORTANT: Be thorough. Extract EVERY criterion, including sub-conditions that are embedded in the text.
Return ONLY valid JSON array, no other text."""


def extract_criteria(tender_text: str, api_key: str = None,
                     progress_callback=None) -> list[dict]:
    """Extract eligibility criteria from tender document text."""

    if progress_callback:
        progress_callback("🔍 Extracting eligibility criteria from tender...")

    messages = [
        SystemMessage(content=CRITERIA_EXTRACTION_PROMPT),
        HumanMessage(content=f"TENDER DOCUMENT:\n\n{tender_text}"),
    ]

    response, provider = try_invoke_with_fallback(
        messages, api_key, max_retries=3, progress_callback=progress_callback,
    )
    content = str(response.content).strip()

    if progress_callback:
        progress_callback(f"✅ Criteria extracted successfully")

    # Extract JSON from response (handle markdown code blocks)
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()

    try:
        criteria = json.loads(content)
        logger.info("Extracted %d criteria", len(criteria))
        return criteria
    except json.JSONDecodeError:
        start = content.find("[")
        end = content.rfind("]") + 1
        if start != -1 and end > start:
            criteria = json.loads(content[start:end])
            logger.info("Extracted %d criteria (fallback parse)", len(criteria))
            return criteria
        raise ValueError(f"Could not parse criteria from LLM response: {content[:200]}")
