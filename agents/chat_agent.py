"""
Chat Agent — LLM-powered Q&A about evaluation reports.
"""
import json
import logging
from langchain_core.messages import SystemMessage, HumanMessage
from utils.llm_utils import try_invoke_with_fallback

logger = logging.getLogger(__name__)

CHAT_SYSTEM_PROMPT = """You are a CRPF procurement evaluation advisor for the TenderSight system.
You have access to the full evaluation report including criteria, bidder verdicts, evidence, and reasoning.

Your role:
1. Answer questions about WHY a bidder was marked eligible/not eligible/manual review
2. Explain the evidence that was used for each decision
3. Compare bidders when asked
4. Explain what "Manual Review" means and what the procurement officer should check
5. Suggest what additional documents could resolve ambiguous cases

Rules:
- Be specific — cite criterion IDs, evidence values, and document sources
- If you don't have enough context, say so clearly
- Always remind the user that final decisions require the authorized procurement officer
- Be concise but thorough
- FORMATTING: You MUST format your response using ONLY standard HTML tags (e.g., <strong>, <br/>, <ul>, <li>, <p>). Do NOT use Markdown asterisks. Make the output structured and easy to read."""

def _build_context_summary(context: dict) -> str:
    """Build a readable summary of the evaluation context for the LLM."""
    parts = []

    criteria = context.get("criteria", [])
    if criteria:
        parts.append(f"CRITERIA ({len(criteria)} total):")
        for c in criteria:
            parts.append(f"  - {c.get('id', '?')}: {c.get('text', '')[:100]}")

    evaluations = context.get("evaluations", {})
    if evaluations:
        parts.append(f"\nBIDDER EVALUATIONS ({len(evaluations)} bidders):")
        for name, ev in evaluations.items():
            parts.append(f"\n  🏢 {name} — Overall: {ev.get('overall_status', '?')}")
            for v in ev.get("verdicts", []):
                status = v.get("status", "?")
                cid = v.get("criterion_id", "?")
                conf = v.get("confidence", 0)
                reasoning = v.get("reasoning", "")[:150]
                evidence = v.get("evidence_used", [])
                ev_summary = ", ".join(
                    f"{e.get('source_document', '?')}: {e.get('value', '?')}"
                    for e in evidence[:3]
                )
                parts.append(
                    f"    [{cid}] {status} (conf: {conf:.0%}) — {reasoning}"
                )
                if ev_summary:
                    parts.append(f"      Evidence: {ev_summary}")

    return "\n".join(parts)


def chat_about_report(question: str, context: dict, api_key: str = None) -> str:
    """Answer a question about the evaluation report."""
    context_summary = _build_context_summary(context)

    messages = [
        SystemMessage(content=CHAT_SYSTEM_PROMPT),
        HumanMessage(content=f"""EVALUATION REPORT CONTEXT:
{context_summary}

USER QUESTION: {question}

Answer clearly and specifically, referencing the data above."""),
    ]

    try:
        response, provider = try_invoke_with_fallback(
            messages, api_key, max_retries=3,
        )
        return str(response.content).strip()
    except Exception as e:
        logger.error("Chat agent failed: %s", e)
        return f"I'm sorry, I couldn't process your question right now. Error: {str(e)}"
