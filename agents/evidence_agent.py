"""
Evidence Extraction Agent — Extracts bidder evidence mapped to each criterion.
"""
import json
import logging
from langchain_core.messages import SystemMessage, HumanMessage
from utils.llm_utils import try_invoke_with_fallback

logger = logging.getLogger(__name__)


EVIDENCE_EXTRACTION_PROMPT = """You are an expert procurement document analyst for CRPF (Central Reserve Police Force).

Given a set of eligibility criteria and a bidder's submission documents, extract the evidence that maps to each criterion.

For each criterion, find and extract:
- "criterion_id": The criterion ID being evaluated
- "value": The specific value/fact found in the bidder's documents (exact numbers, dates, counts). MUST be a string.
- "source_document": Which document section the evidence was found in (e.g., "CA Certificate", "Experience Certificates")
- "source_section": More specific location
- "confidence": Your confidence in the extraction (0.0 to 1.0)
  - 1.0 = clearly stated with no ambiguity
  - 0.7-0.9 = stated but requires interpretation
  - 0.5-0.7 = inferred or partially available
  - below 0.5 = uncertain or missing
- "raw_excerpt": The exact text excerpt from the document that contains this evidence

If evidence for a criterion is NOT found in the documents, still include an entry with:
- "value": "NOT FOUND"
- "confidence": 0.0
- "raw_excerpt": "No relevant evidence found in submission documents"

IMPORTANT: All "value" fields must be strings, never numbers.
Return ONLY a valid JSON array of evidence objects. Be precise with numbers and dates."""


def extract_evidence(criteria: list[dict], bidder_text: str, bidder_name: str,
                     api_key: str = None, progress_callback=None) -> list[dict]:
    """Extract evidence from bidder submission mapped to each criterion."""

    if progress_callback:
        progress_callback(f"🔍 Extracting evidence from {bidder_name}'s documents...")

    criteria_text = json.dumps(criteria, indent=2)

    messages = [
        SystemMessage(content=EVIDENCE_EXTRACTION_PROMPT),
        HumanMessage(content=f"""ELIGIBILITY CRITERIA:
{criteria_text}

BIDDER NAME: {bidder_name}

BIDDER SUBMISSION DOCUMENTS:
{bidder_text}"""),
    ]

    response, provider = try_invoke_with_fallback(
        messages, api_key, max_retries=3, progress_callback=progress_callback,
    )
    content = str(response.content).strip()

    if progress_callback:
        progress_callback(f"✅ Evidence extracted for {bidder_name}")

    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()

    try:
        evidence = json.loads(content)
        # Ensure all values are correct types (prevent int.strip() errors)
        for e in evidence:
            if "value" in e:
                e["value"] = str(e["value"])
            if "confidence" in e:
                try:
                    e["confidence"] = float(e["confidence"])
                except (ValueError, TypeError):
                    e["confidence"] = 0.5
            if "raw_excerpt" in e:
                e["raw_excerpt"] = str(e.get("raw_excerpt", ""))
            if "source_document" in e:
                e["source_document"] = str(e.get("source_document", ""))
            if "criterion_id" in e:
                e["criterion_id"] = str(e["criterion_id"])
        logger.info("Extracted %d evidence fragments for %s", len(evidence), bidder_name)
        return evidence
    except json.JSONDecodeError:
        start = content.find("[")
        end = content.rfind("]") + 1
        if start != -1 and end > start:
            evidence = json.loads(content[start:end])
            for e in evidence:
                if "value" in e:
                    e["value"] = str(e["value"])
            return evidence
        raise ValueError(f"Could not parse evidence from LLM response: {content[:200]}")
