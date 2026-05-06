import json
import logging
from langchain_core.messages import SystemMessage, HumanMessage
from utils.llm_utils import try_invoke_with_fallback

logger = logging.getLogger(__name__)

EXTRACT_PROMPT = """You are a Corporate Metadata Extractor.
Given the text from a bidder's tender submission, extract the following corporate details:
- director_name: The name of the main Director / Managing Director / CEO / Authorized Signatory
- address: The Registered Office Address or Corporate Address

Return ONLY a valid JSON object like:
{"director_name": "Rajesh Kumar", "address": "Plot 42, Tech Park, Hyderabad"}

If a field is not found, use null. Do NOT invent data.
"""


def detect_cartels_via_graph(tender_id: str, evaluations: dict, api_key: str = None) -> list:
    """
    In-Memory Graph Analyzer for Cartel & Shell Company Detection.
    
    Extracts corporate metadata (Director, Address) from each bidder's document
    using LLM, then cross-references all bidders to find suspicious overlaps.
    
    Returns a list of alerts:
      [{"bidder1": "A", "bidder2": "B", "shared_entity": "Rajesh Kumar", "link_type": "Director"}]
    """
    if len(evaluations) < 2:
        return []

    # Step 1: Extract corporate metadata from each bidder using LLM
    metadata_map = {}
    for bidder, ev in evaluations.items():
        text = ev.get("bidder_text_snapshot", "")
        if not text:
            continue

        messages = [
            SystemMessage(content=EXTRACT_PROMPT),
            HumanMessage(content=f"Extract metadata from this bidder document:\n\n{text[:12000]}")
        ]

        try:
            resp = try_invoke_with_fallback(messages, api_key=api_key)
            start = resp.find('{')
            end = resp.rfind('}') + 1
            if start != -1 and end > 0:
                data = json.loads(resp[start:end])
                metadata_map[bidder] = data
                logger.info(f"Extracted metadata for {bidder}: {data}")
        except Exception as e:
            logger.error(f"Metadata extraction failed for {bidder}: {e}")

    # Step 2: Cross-reference all bidders for overlapping entities
    cartel_alerts = []
    bidders = list(metadata_map.keys())

    for i in range(len(bidders)):
        for j in range(i + 1, len(bidders)):
            b1, b2 = bidders[i], bidders[j]
            m1, m2 = metadata_map[b1], metadata_map[b2]

            d1 = (m1.get("director_name") or "").strip().lower()
            d2 = (m2.get("director_name") or "").strip().lower()
            a1 = (m1.get("address") or "").strip().lower()
            a2 = (m2.get("address") or "").strip().lower()

            # Check Director overlap
            if d1 and d2 and d1 == d2:
                cartel_alerts.append({
                    "bidder1": b1,
                    "bidder2": b2,
                    "shared_entity": m1.get("director_name"),
                    "link_type": "Director",
                })

            # Check Address overlap
            if a1 and a2 and a1 == a2:
                cartel_alerts.append({
                    "bidder1": b1,
                    "bidder2": b2,
                    "shared_entity": m1.get("address"),
                    "link_type": "Address",
                })

    if cartel_alerts:
        logger.warning(f"⚠️ CARTEL DETECTION: {len(cartel_alerts)} suspicious links found!")

    return cartel_alerts
