import json
import logging
import statistics
from langchain_core.messages import SystemMessage, HumanMessage
from utils.llm_utils import try_invoke_with_fallback

logger = logging.getLogger(__name__)

ANOMALY_PROMPT = """You are a Financial Data Extraction Assistant.
Given a JSON mapping of bidders to their tender evaluation results, your ONLY job is to extract the TOTAL financial bid amount proposed by each bidder.
Look for criteria mentioning "Financial Bid", "Price", "Cost", or "Quote".
Convert the text values into a single pure numeric float in INR (e.g., "Rs. 8.21 Crore" -> 82100000.0, "45 Lakhs" -> 4500000.0).

Return ONLY a valid JSON dictionary mapping the bidder's name exactly as provided to their numeric float value.
If a bidder has no financial bid data, map their name to null.

Example Output:
{
  "Bidder A": 82100000.0,
  "Bidder B": 4500000.0,
  "Bidder C": null
}
"""

def detect_financial_anomalies(evaluations: dict, api_key: str = None) -> dict:
    """
    Takes the full evaluations dictionary.
    Extracts numerical bids using LLM, then calculates statistical anomalies.
    Returns the original evaluations dict with anomaly flags injected.
    """
    if len(evaluations) < 2:
        return evaluations # Need at least 2 bidders for any meaningful comparison, ideally 3+

    # Prepare data for LLM
    extraction_payload = {}
    for bidder, eval_data in evaluations.items():
        # Only send the extracted values to save context
        evidence = [v.get("evidence_value", "") for v in eval_data.get("verdicts", [])]
        extraction_payload[bidder] = evidence
        
    messages = [
        SystemMessage(content=ANOMALY_PROMPT),
        HumanMessage(content=f"Extract bids from this data:\n{json.dumps(extraction_payload, indent=2)}")
    ]

    try:
        response, _ = try_invoke_with_fallback(messages, api_key=api_key)
        response_text = response.content
        # Parse JSON
        start = response_text.find('{')
        end = response_text.rfind('}') + 1
        if start != -1 and end != 0:
            numeric_bids = json.loads(response_text[start:end])
        else:
            return evaluations
            
        # Filter out nulls
        valid_bids = {k: v for k, v in numeric_bids.items() if v is not None and isinstance(v, (int, float))}
        
        if len(valid_bids) < 2:
            return evaluations
            
        # Calculate stats
        values = list(valid_bids.values())
        mean_bid = statistics.mean(values)
        stdev_bid = statistics.stdev(values) if len(values) > 1 else 0.0
        
        # Inject anomaly flags
        for bidder in evaluations.keys():
            evaluations[bidder]["anomaly_flag"] = False
            evaluations[bidder]["anomaly_reason"] = None
            evaluations[bidder]["financial_bid_numeric"] = valid_bids.get(bidder)
            
            if bidder in valid_bids and stdev_bid > 0:
                val = valid_bids[bidder]
                z_score = (val - mean_bid) / stdev_bid
                
                if z_score < -1.1:
                    evaluations[bidder]["anomaly_flag"] = True
                    evaluations[bidder]["anomaly_reason"] = f"Abnormally Low Bid (Z-score: {z_score:.2f}). This is statistically significantly lower than the average bid of {mean_bid:,.2f} INR and poses a potential quality or feasibility risk."
                elif z_score > 1.1:
                    evaluations[bidder]["anomaly_flag"] = True
                    evaluations[bidder]["anomaly_reason"] = f"Abnormally High Bid (Z-score: {z_score:.2f}). This bid is significantly higher than the market median for this tender."
                    
        return evaluations

    except Exception as e:
        logger.error(f"Anomaly detection failed: {e}")
        return evaluations
