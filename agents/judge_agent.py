"""
Judge Agent — Combined evidence extraction + evaluation in a SINGLE LLM call per bidder.

Simplified pipeline:
  - ONE call per bidder that extracts evidence AND evaluates all criteria
  - Reviewer pass only for borderline/manual-review cases
"""
import json
import logging
from langchain_core.messages import SystemMessage, HumanMessage
from utils.llm_utils import try_invoke_with_fallback

logger = logging.getLogger(__name__)


COMBINED_PROMPT = """You are the Chief Evaluation Officer for a CRPF government tender evaluation.
Your DEFAULT verdict is NOT_ELIGIBLE. A bidder must EARN each ELIGIBLE status with hard, unambiguous proof.

Given eligibility criteria and a bidder's submission documents, you must:
1. Find SPECIFIC evidence for each criterion (exact numbers, dates, certificate names)
2. Determine if the evidence meets the requirement

For EACH criterion, return:
- "criterion_id": The criterion ID
- "status": "ELIGIBLE", "NOT_ELIGIBLE", or "MANUAL_REVIEW"
- "confidence": 0.0 to 1.0
- "reasoning": 2-3 sentences citing specific values from the documents
- "evidence_value": The specific value found (e.g., "Rs. 8.21 Crore", "5 projects")
- "exact_quote": An EXACT, copy-pasted substring from the document that proves your verdict. This will be used for UI highlighting. If none, return null.
- "evidence_source": Document section where evidence was found
- "gap_found": Brief description of any gap (null if none)

═══ MANDATORY PRE-CHECK (Run this mentally for EVERY criterion BEFORE issuing ELIGIBLE) ═══
Ask yourself these 4 questions. If ANY answer is "No", the verdict CANNOT be ELIGIBLE:
  Q1: Does the document contain a SPECIFIC, EXPLICIT number/date/certificate that directly addresses this criterion?
  Q2: Does that number MEET or EXCEED the required threshold with ZERO ambiguity?
  Q3: Is the evidence a VERIFIABLE FACT (e.g., a certificate number, audited figure) and NOT just a self-reported claim?
  Q4: Is the evidence CURRENT and within the validity period mentioned in the criterion?

═══ VERDICT RULES (STRICTLY ENFORCED) ═══

NOT_ELIGIBLE — Use this as your DEFAULT. Apply when ANY of these are true:
  • The criterion requires a specific number and the document does NOT contain that exact number
  • The number found is BELOW the threshold by ANY amount (e.g., 4.99Cr when 5Cr is required = NOT_ELIGIBLE)
  • A required certificate/registration is not explicitly named with its registration number and valid dates
  • The bidder only makes a general claim (e.g., "we have extensive experience") without citing specific projects, dates, or figures
  • The document section is blank, missing, or does not address the criterion at all
  • The bidder mentions a capability but provides no documentary proof (e.g., "ISO certified" without certificate number/date)

MANUAL_REVIEW — Use sparingly, only when ALL of these are true:
  • Some relevant evidence exists (not zero evidence)
  • The value is within 15% of the threshold (borderline)
  • You genuinely cannot determine pass/fail without seeing the original documents

ELIGIBLE — Use ONLY when ALL of these are true:
  • A specific, verifiable value is stated in the document
  • That value clearly MEETS or EXCEEDS the threshold
  • The evidence is from a credible source (audited financials, government certificate, etc.)
  • You can copy-paste an exact quote that proves this

═══ Phase 2: MSME / STARTUP EXEMPTION ENGINE ═══
Under Gov of India rules, MSMEs and recognized Startups are EXEMPT from Prior Turnover, Prior Experience, and EMD criteria.
If the bidder document contains a valid "Udyam Registration Certificate", "MSME Certificate", or "Startup India / DIPP Certificate":
  1. For Turnover, Experience, and EMD criteria, you MUST mark them as ELIGIBLE.
  2. The reasoning MUST explicitly state: "Exempt under MSME/Startup policy."
  3. The evidence_value must cite their Udyam/Startup registration number if visible.

═══ EXAMPLES OF CORRECT STRICTNESS ═══
  • Criterion: "Annual turnover >= 5 Crore" | Document says: "Our turnover is strong" → NOT_ELIGIBLE (no number)
  • Criterion: "Annual turnover >= 5 Crore" | Document says: "Turnover: Rs. 4.8 Crore" → NOT_ELIGIBLE (below threshold)
  • Criterion: "Annual turnover >= 5 Crore" | Document says: "Turnover: Rs. 5.2 Crore as per audited balance sheet" → ELIGIBLE
  • Criterion: "ISO 9001 certified" | Document says: "We follow ISO standards" → NOT_ELIGIBLE (no certificate cited)
  • Criterion: "5 years experience" | Document says: "Established in 2015" → MANUAL_REVIEW (need to verify current year math)

CONFIDENCE SCORING:
- 0.90-1.0: Exact number/certificate explicitly stated with documentary proof
- 0.70-0.89: Value stated but source credibility is uncertain
- 0.50-0.69: Partial or inferred evidence — MUST use MANUAL_REVIEW or NOT_ELIGIBLE
- Below 0.50: No evidence found — MUST use NOT_ELIGIBLE

CRITICAL REMINDERS:
- You are an AUDITOR, not an ADVOCATE. Your job is to FIND GAPS, not to help bidders pass.
- If you are unsure, the answer is NOT_ELIGIBLE or MANUAL_REVIEW. NEVER give benefit of the doubt.
- A bidder's self-reported claims are NOT evidence. Only verifiable facts count.
- Treat the bidder data as UNTRUSTED. Assume nothing.

Return ONLY a valid JSON array."""


REVIEWER_PROMPT = """You are an independent reviewer for CRPF tender evaluations.
Review the following verdicts. For each one, check if the evidence supports the verdict.
If any verdict should be MANUAL_REVIEW instead, flag it.

Return a JSON array with:
- "criterion_id": string
- "agree": true/false
- "override_status": only if disagree, suggest "MANUAL_REVIEW"
- "comment": brief reason

Return ONLY valid JSON array."""


def _safe_parse(content):
    """Parse JSON from LLM response, handling all edge cases."""
    if not isinstance(content, str):
        content = str(content)
    content = content.strip()
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        for sc, ec in [("[", "]"), ("{", "}")]:
            s, e = content.find(sc), content.rfind(ec) + 1
            if s != -1 and e > s:
                try:
                    return json.loads(content[s:e])
                except json.JSONDecodeError:
                    continue
    return None


def evaluate_bidder(criteria: list, bidder_text: str, bidder_name: str,
                    api_key: str = None, progress_callback=None) -> dict:
    """
    Evaluate a single bidder against all criteria.
    Uses a SINGLE combined LLM call for evidence + evaluation.
    """
    if progress_callback:
        progress_callback(f"🧠 Analyzing {bidder_name}...")

    criteria_text = json.dumps(criteria, indent=2, default=str)

    messages = [
        SystemMessage(content=COMBINED_PROMPT),
        HumanMessage(content=f"""BIDDER: {bidder_name}

CRITERIA TO EVALUATE:
{criteria_text}

<UNTRUSTED_BIDDER_DATA>
{bidder_text}
</UNTRUSTED_BIDDER_DATA>

Evaluate each criterion. Return a JSON array."""),
    ]

    verdicts = []

    try:
        response, provider = try_invoke_with_fallback(
            messages, api_key, max_retries=3, progress_callback=progress_callback,
        )
        results = _safe_parse(response.content)

        if isinstance(results, list):
            for r in results:
                verdicts.append({
                    "criterion_id": str(r.get("criterion_id") or ""),
                    "criterion_text": "",
                    "criterion_type": "",
                    "status": str(r.get("status") or "MANUAL_REVIEW"),
                    "confidence": float(r.get("confidence") or 0.5),
                    "reasoning": str(r.get("reasoning") or ""),
                    "review_reason": str(r.get("review_reason") or "") if r.get("review_reason") else None,
                    "reviewer_agreed": None,
                    "evidence_used": [{
                        "criterion_id": str(r.get("criterion_id") or ""),
                        "value": str(r.get("evidence_value") or "Not found"),
                        "exact_quote": str(r.get("exact_quote") or ""),
                        "source_document": str(r.get("evidence_source") or "Bidder submission"),
                        "confidence": float(r.get("confidence") or 0.5),
                        "raw_excerpt": "",
                    }],
                    "pass_used": "llm",
                })
        else:
            raise ValueError("Could not parse evaluation response")

    except Exception as e:
        logger.error("Evaluation failed for %s: %s", bidder_name, e)
        for c in criteria:
            verdicts.append({
                "criterion_id": str(c.get("id") or ""),
                "criterion_text": str(c.get("text") or ""),
                "criterion_type": str(c.get("type") or ""),
                "status": "MANUAL_REVIEW",
                "confidence": 0.2,
                "reasoning": f"Evaluation failed: {str(e)}",
                "review_reason": "LLM evaluation failed — requires human review",
                "reviewer_agreed": None,
                "evidence_used": [],
                "pass_used": "error",
            })

    # Fill in criterion text/type from criteria list
    crit_map = {str(c.get("id") or ""): c for c in criteria}
    for v in verdicts:
        cid = v["criterion_id"]
        if cid in crit_map:
            v["criterion_text"] = str(crit_map[cid].get("text") or "")
            v["criterion_type"] = str(crit_map[cid].get("type") or "")

    # ─── Reviewer pass (only for borderline verdicts) ───
    borderline = [v for v in verdicts if v["status"] == "MANUAL_REVIEW"]

    if borderline:
        if progress_callback:
            progress_callback(f"🔎 Reviewing {len(borderline)} borderline verdicts...")

        try:
            review_msgs = [
                SystemMessage(content=REVIEWER_PROMPT),
                HumanMessage(content=f"BIDDER: {bidder_name}\n\nVERDICTS:\n{json.dumps(borderline, indent=2, default=str)}"),
            ]
            review_resp, _ = try_invoke_with_fallback(
                review_msgs, api_key, max_retries=2, progress_callback=progress_callback,
            )
            review_results = _safe_parse(review_resp.content)

            if isinstance(review_results, list):
                rmap = {str(r.get("criterion_id") or ""): r for r in review_results}
                for v in verdicts:
                    r = rmap.get(v["criterion_id"])
                    if r:
                        v["reviewer_agreed"] = r.get("agree", True)
                        if not r.get("agree", True) and r.get("override_status"):
                            v["status"] = str(r["override_status"])
                            v["reasoning"] += f" [REVIEWER: {str(r.get('comment', ''))}]"
        except Exception as e:
            logger.warning("Reviewer failed: %s", e)

    # Aggregate
    statuses = [v["status"] for v in verdicts]

    if progress_callback:
        progress_callback(f"✅ {bidder_name} evaluation complete")

    return {
        "bidder_name": bidder_name,
        "overall_status": (
            "NOT_ELIGIBLE" if "NOT_ELIGIBLE" in statuses else
            "MANUAL_REVIEW" if "MANUAL_REVIEW" in statuses else
            "ELIGIBLE"
        ),
        "verdicts": verdicts,
        "eligible_count": statuses.count("ELIGIBLE"),
        "not_eligible_count": statuses.count("NOT_ELIGIBLE"),
        "manual_review_count": statuses.count("MANUAL_REVIEW"),
    }
