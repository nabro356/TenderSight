"""
TenderSight — AI-Powered Tender Evaluation & Eligibility Analysis
Main Streamlit Application (Live Agent Mode)
"""
import streamlit as st
import json
import time
from pathlib import Path
from datetime import datetime

from agents.ingestion_agent import ingest_document
from agents.security_agent import check_security
from agents.criteria_agent import extract_criteria
from agents.evidence_agent import extract_evidence
from agents.judge_agent import evaluate_bidder
from utils.report_generator import generate_pdf_report
from config import NVIDIA_API_KEY, SAMPLE_DATA_DIR, COLORS

# ─── Page Config ───
st.set_page_config(
    page_title="TenderSight — CRPF Tender Evaluation",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Load CSS ───
css_path = Path(__file__).parent / "assets" / "style.css"
if css_path.exists():
    st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)


# ─── Session State Init ───
def init_state():
    defaults = {
        "step": 1,
        "api_key": NVIDIA_API_KEY,
        "tender_text": "",
        "criteria": [],
        "bidders": {},
        "evidence": {},
        "evaluations": {},
        "processing": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()


# ─── UI Helpers ───
def render_hero():
    st.markdown("""
    <div class="hero-header">
        <h1>⚖️ TenderSight</h1>
        <p>AI-Powered Tender Evaluation & Eligibility Analysis for CRPF Government Procurement</p>
    </div>
    """, unsafe_allow_html=True)


def render_progress():
    steps = [
        ("📄", "Upload Tender"),
        ("📁", "Load Bidders"),
        ("⚖️", "Evaluate"),
        ("📊", "Report"),
    ]
    current = st.session_state.step
    items_html = ""
    for i, (icon, label) in enumerate(steps, 1):
        if i < current:
            cls, num = "completed", "✓"
        elif i == current:
            cls, num = "active", str(i)
        else:
            cls, num = "", str(i)
        items_html += f"""
        <div class="step-item {cls}">
            <div class="step-number">{num}</div>
            <span>{icon} {label}</span>
        </div>"""
    st.markdown(f'<div class="step-progress">{items_html}</div>', unsafe_allow_html=True)


def verdict_badge(status):
    if status == "ELIGIBLE":
        return '<span class="verdict-badge verdict-eligible">✅ ELIGIBLE</span>'
    elif status == "NOT_ELIGIBLE":
        return '<span class="verdict-badge verdict-not-eligible">❌ NOT ELIGIBLE</span>'
    else:
        return '<span class="verdict-badge verdict-manual-review">⚠️ MANUAL REVIEW</span>'


def criterion_type_badge(ctype):
    cls = f"type-{ctype.lower()}"
    return f'<span class="criterion-type {cls}">{ctype}</span>'


def confidence_bar(confidence):
    pct = int(confidence * 100)
    if confidence >= 0.85:
        color = "#16a34a"
    elif confidence >= 0.65:
        color = "#d97706"
    else:
        color = "#dc2626"
    return f"""
    <div class="confidence-bar-bg">
        <div class="confidence-bar" style="width:{pct}%;background:{color};"></div>
    </div>
    <span style="font-size:0.75rem;color:#64748b;">Confidence: {pct}%</span>
    """


def load_sample_tender():
    tender_path = SAMPLE_DATA_DIR / "tender.txt"
    if tender_path.exists():
        return tender_path.read_text(encoding="utf-8")
    return ""


def load_sample_bidders():
    bidders_dir = SAMPLE_DATA_DIR / "bidders"
    bidders = {}
    if bidders_dir.exists():
        for f in sorted(bidders_dir.glob("*.txt")):
            name = f.stem.replace("_", " ").title()
            bidders[name] = f.read_text(encoding="utf-8")
    return bidders


# ─── Sidebar ───
with st.sidebar:
    st.markdown("### ⚙️ Configuration")
    api_key = st.text_input(
        "NVIDIA API Key",
        value=st.session_state.api_key,
        type="password",
        help="Enter your NVIDIA API key for ChatNVIDIA"
    )
    if api_key:
        st.session_state.api_key = api_key

    st.divider()
    st.markdown("### 📋 Navigation")
    if st.button("🔄 Reset Evaluation", use_container_width=True):
        for k in ["step", "tender_text", "criteria", "bidders", "evidence", "evaluations", "processing"]:
            if k in st.session_state:
                del st.session_state[k]
        init_state()
        st.rerun()

    st.divider()
    st.markdown("""
    <div style="padding:1rem;background:#f1f5f9;border-radius:10px;font-size:0.8rem;color:#64748b;">
        <strong>TenderSight v2.0</strong><br>
        Powered by NVIDIA AI<br>
        Multi-Provider Fallback<br><br>
        <em>Every verdict is explainable.<br>
        No silent disqualification.</em>
    </div>
    """, unsafe_allow_html=True)


# ─── Main Content ───
render_hero()
render_progress()


# ═══════════════════════════════════════
# STEP 1: Upload Tender
# ═══════════════════════════════════════
if st.session_state.step == 1:
    st.markdown("## 📄 Step 1: Tender Document")
    st.markdown("Upload a tender document or use the sample CRPF tender to extract eligibility criteria.")

    col1, col2 = st.columns([3, 1])
    with col1:
        uploaded = st.file_uploader("Upload Tender Document (.txt, .pdf)", type=["txt", "pdf"], key="tender_upload")
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        use_sample = st.button("📋 Sample Tender", use_container_width=True)

    if use_sample:
        st.session_state.tender_text = load_sample_tender()
        st.rerun()

    if uploaded:
        file_bytes = uploaded.read()
        with st.spinner("📄 Processing document..."):
            result = ingest_document(file_bytes, uploaded.name, api_key=st.session_state.api_key)
            st.session_state.tender_text = result["raw_text"]
            if result["tier_used"] != "text_file":
                st.info(f"📄 Extracted via **{result['tier_used']}** — {result['pages']} pages, {result['confidence']:.0%} confidence")
        st.rerun()

    if st.session_state.tender_text:
        with st.expander("📖 Tender Document Preview", expanded=False):
            st.text(st.session_state.tender_text[:3000] + ("..." if len(st.session_state.tender_text) > 3000 else ""))

        if st.button("🔍 Extract Eligibility Criteria", use_container_width=True, type="primary"):
            status_box = st.empty()
            with st.spinner("🤖 AI Agent extracting criteria..."):
                try:
                    criteria = extract_criteria(
                        st.session_state.tender_text,
                        api_key=st.session_state.api_key,
                        progress_callback=lambda msg: status_box.markdown(f"**{msg}**"),
                    )
                    st.session_state.criteria = criteria
                    st.success(f"✅ Extracted **{len(criteria)}** eligibility criteria!")
                    time.sleep(1)
                    st.session_state.step = 2
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Criteria extraction failed: {e}")

    if not st.session_state.tender_text:
        st.info("💡 Click **Sample Tender** to load a pre-built CRPF construction tender.")


# ═══════════════════════════════════════
# STEP 2: Load Bidders
# ═══════════════════════════════════════
elif st.session_state.step == 2:
    st.markdown("## 📁 Step 2: Bidder Submissions")

    # Show extracted criteria
    st.markdown("### Extracted Eligibility Criteria")
    type_icons = {"Financial": "💰", "Experience": "🏗️", "Compliance": "📋", "Technical": "⚙️"}
    for i, c in enumerate(st.session_state.criteria):
        ctype = c.get("type", "General")
        cid = c.get("id", f"C-{i+1}")
        icon = type_icons.get(ctype, "📌")
        with st.expander(f"{icon} [{ctype}] {cid}: {c.get('text', '')[:90]}...", expanded=False):
            st.markdown(f"**Full Text:** {c.get('text', '')}")
            st.markdown(f"**Mandatory:** {'✅ Yes' if c.get('mandatory', True) else '❌ No'}")
            st.markdown(f"**Section:** {c.get('source_section', 'N/A')}")
            if c.get("sub_conditions"):
                st.markdown("**Sub-conditions:**")
                for sc in c["sub_conditions"]:
                    st.markdown(f"- `{sc.get('parameter', '')}` {sc.get('operator', '')} `{sc.get('threshold', '')}` {sc.get('unit', '')}")

    st.divider()
    st.markdown("### Load Bidder Submissions")

    col1, col2 = st.columns([3, 1])
    with col1:
        uploaded_bidders = st.file_uploader(
            "Upload Bidder Documents (.txt, .pdf)",
            type=["txt", "pdf"],
            accept_multiple_files=True,
            key="bidder_upload"
        )
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        use_sample_bidders = st.button("📋 Sample Bidders", use_container_width=True)

    if use_sample_bidders:
        st.session_state.bidders = load_sample_bidders()
        st.rerun()

    if uploaded_bidders:
        for f in uploaded_bidders:
            file_bytes = f.read()
            name = f.name.replace(".txt", "").replace(".pdf", "").replace("_", " ").title()
            with st.spinner(f"📄 Processing {name}..."):
                result = ingest_document(file_bytes, f.name, api_key=st.session_state.api_key)
                st.session_state.bidders[name] = result["raw_text"]
                if result["tier_used"] != "text_file":
                    st.info(f"📄 {name}: {result['tier_used']} — {result['confidence']:.0%} confidence")
        st.rerun()

    if st.session_state.bidders:
        st.markdown(f"**{len(st.session_state.bidders)} bidders loaded:**")
        for name in st.session_state.bidders:
            st.markdown(f"- 🏢 {name}")

        if st.button("⚖️ Proceed to Evaluation", use_container_width=True, type="primary"):
            st.session_state.step = 3
            st.rerun()

    if not st.session_state.bidders:
        st.info("💡 Click **Sample Bidders** to load 4 sample bidders.")


# ═══════════════════════════════════════
# STEP 3: Evaluate
# ═══════════════════════════════════════
elif st.session_state.step == 3:
    st.markdown("## ⚖️ Step 3: Evaluation")

    if not st.session_state.evaluations:
        st.markdown("Ready to evaluate **{}** bidders against **{}** criteria.".format(
            len(st.session_state.bidders), len(st.session_state.criteria)
        ))
        st.markdown("""
        <div class="eval-card">
            <strong>🤖 Live Evaluation Pipeline:</strong>
            <ol style="margin-top:0.5rem;color:#475569;font-size:0.9rem;">
                <li><strong>Security Scan</strong> — Check for prompt injection & adversarial content</li>
                <li><strong>Evidence Extraction</strong> — AI extracts relevant evidence from each bidder</li>
                <li><strong>Pass 1: Deterministic Check</strong> — Numeric criteria evaluated programmatically</li>
                <li><strong>Pass 2: LLM Reasoning</strong> — Qualitative criteria with chain-of-thought</li>
                <li><strong>Pass 3: LLM Reviewer</strong> — Independent review for errors</li>
            </ol>
            <p style="margin-top:0.5rem;color:#64748b;font-size:0.8rem;">
                ⏱️ Provider fallback: NVIDIA → Gemini → Groq. Rate-limit pauses shown in real-time.
            </p>
        </div>
        """, unsafe_allow_html=True)

        if st.button("🚀 Run Full Evaluation", use_container_width=True, type="primary"):
            progress = st.progress(0)
            status_text = st.empty()
            detail_text = st.empty()
            bidder_names = list(st.session_state.bidders.keys())
            total = len(bidder_names)

            for idx, name in enumerate(bidder_names):
                status_text.markdown(f"**⚖️ [{idx+1}/{total}] Evaluating {name}...**")

                try:
                    # Security check
                    detail_text.markdown("🛡️ Security scan...")
                    security = check_security(st.session_state.bidders[name], filename=name)

                    if not security["safe"]:
                        detail_text.markdown(f"⚠️ Security: {len(security['threats_detected'])} issue(s) found")

                    clean_text = security["sanitized_text"]

                    # Evidence extraction
                    detail_text.markdown(f"🔍 Extracting evidence for {name}...")
                    evidence = extract_evidence(
                        st.session_state.criteria,
                        clean_text,
                        name,
                        api_key=st.session_state.api_key,
                        progress_callback=lambda msg: detail_text.markdown(msg),
                    )

                    # 3-pass evaluation
                    detail_text.markdown(f"⚖️ Running 3-pass evaluation for {name}...")
                    evaluation = evaluate_bidder(
                        st.session_state.criteria,
                        evidence,
                        name,
                        api_key=st.session_state.api_key,
                        progress_callback=lambda msg: detail_text.markdown(msg),
                    )

                    evaluation["security_report"] = security
                    st.session_state.evaluations[name] = evaluation

                except Exception as e:
                    st.error(f"❌ Evaluation failed for {name}: {e}")
                    st.session_state.evaluations[name] = {
                        "bidder_name": name,
                        "overall_status": "MANUAL_REVIEW",
                        "verdicts": [],
                        "eligible_count": 0,
                        "not_eligible_count": 0,
                        "manual_review_count": len(st.session_state.criteria),
                        "error": str(e),
                    }

                progress.progress((idx + 1) / total)

            status_text.markdown("**✅ Evaluation complete!**")
            detail_text.empty()
            time.sleep(1)
            st.rerun()

    else:
        # ─── Show Results ───
        evaluations = st.session_state.evaluations

        eligible = sum(1 for e in evaluations.values() if e["overall_status"] == "ELIGIBLE")
        not_eligible = sum(1 for e in evaluations.values() if e["overall_status"] == "NOT_ELIGIBLE")
        manual_review = sum(1 for e in evaluations.values() if e["overall_status"] == "MANUAL_REVIEW")

        st.markdown("### 📊 Evaluation Summary")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-number" style="color:#1e40af;">{len(evaluations)}</div>
                <div class="stat-label">Total Bidders</div>
            </div>""", unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-number" style="color:#16a34a;">{eligible}</div>
                <div class="stat-label">Eligible</div>
            </div>""", unsafe_allow_html=True)
        with c3:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-number" style="color:#dc2626;">{not_eligible}</div>
                <div class="stat-label">Not Eligible</div>
            </div>""", unsafe_allow_html=True)
        with c4:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-number" style="color:#d97706;">{manual_review}</div>
                <div class="stat-label">Manual Review</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### 📋 Bidder Evaluations")

        for name, evaluation in evaluations.items():
            overall = evaluation["overall_status"]
            css_class = overall.lower().replace("_", "-")

            with st.expander(
                f"{'✅' if overall == 'ELIGIBLE' else '❌' if overall == 'NOT_ELIGIBLE' else '⚠️'} {name} — {overall.replace('_', ' ')}",
                expanded=(overall != "ELIGIBLE")
            ):
                if evaluation.get("error"):
                    st.error(f"⚠️ Evaluation error: {evaluation['error']}")
                    continue

                st.markdown(f"""
                <div class="bidder-card {css_class}">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <h3 style="margin:0;color:#1e293b;">🏢 {name}</h3>
                        {verdict_badge(overall)}
                    </div>
                    <div style="margin-top:0.75rem;color:#64748b;font-size:0.85rem;">
                        ✅ {evaluation['eligible_count']} Eligible &nbsp;|&nbsp;
                        ❌ {evaluation['not_eligible_count']} Not Eligible &nbsp;|&nbsp;
                        ⚠️ {evaluation['manual_review_count']} Manual Review
                    </div>
                </div>
                """, unsafe_allow_html=True)

                for v in evaluation.get("verdicts", []):
                    status = v.get("status", "MANUAL_REVIEW")
                    ctype = v.get("criterion_type", "General")
                    conf = v.get("confidence", 0.5)
                    pass_used = v.get("pass_used", "llm")
                    pass_label = "🔢 Deterministic" if pass_used == "deterministic" else "🧠 LLM"

                    st.markdown(f"""<div class="eval-card"><div style="display:flex;justify-content:space-between;align-items:flex-start;"><div>{criterion_type_badge(ctype)} <strong style="margin-left:0.5rem;">{v.get('criterion_id', '')}</strong> <span style="color:#64748b;margin-left:0.5rem;font-size:0.85rem;">{v.get('criterion_text', '')[:80]}...</span></div><div>{verdict_badge(status)} <span style="font-size:0.7rem;color:#94a3b8;margin-left:0.5rem;">{pass_label}</span></div></div>{confidence_bar(conf)}</div>""", unsafe_allow_html=True)

                    if v.get("reasoning"):
                        st.markdown(f"""<div class="reasoning-box">
                            <strong>💭 Reasoning:</strong> {v['reasoning']}
                        </div>""", unsafe_allow_html=True)

                    if v.get("review_reason"):
                        st.warning(f"⚠️ **Review Required:** {v['review_reason']}")

                    evidence_used = v.get("evidence_used", [])
                    if evidence_used:
                        for ev in evidence_used:
                            doc = ev.get("source_document", "Unknown")
                            val = ev.get("value", "N/A")
                            excerpt = ev.get("raw_excerpt", "")
                            ev_conf = ev.get("confidence", 0)
                            st.markdown(f"""<div class="evidence-chain">
                                <div class="doc-ref">📄 {doc}</div>
                                <div class="value">Value: <strong>{val}</strong> (confidence: {int(ev_conf*100)}%)</div>
                                {f'<div style="margin-top:0.25rem;color:#64748b;font-size:0.8rem;font-style:italic;">"{excerpt[:150]}..."</div>' if excerpt and excerpt != "N/A" else ''}
                            </div>""", unsafe_allow_html=True)

                    st.markdown("<br>", unsafe_allow_html=True)

        st.divider()
        if st.button("📊 Generate Evaluation Report", use_container_width=True, type="primary"):
            st.session_state.step = 4
            st.rerun()


# ═══════════════════════════════════════
# STEP 4: Report
# ═══════════════════════════════════════
elif st.session_state.step == 4:
    st.markdown("## 📊 Step 4: Evaluation Report")

    evaluations = st.session_state.evaluations
    criteria = st.session_state.criteria

    st.markdown(f"""
    <div class="eval-card" style="border-left:4px solid #1e40af;">
        <h3 style="margin:0 0 0.5rem 0;color:#1e40af;">📋 Consolidated Evaluation Report</h3>
        <table style="font-size:0.85rem;color:#475569;">
            <tr><td style="padding-right:1rem;"><strong>Tender:</strong></td><td>Construction of Border Outpost Buildings — CRPF</td></tr>
            <tr><td><strong>Reference:</strong></td><td>CRPF/CE/2025-26/BOP-CONSTR/047</td></tr>
            <tr><td><strong>Criteria Count:</strong></td><td>{len(criteria)}</td></tr>
            <tr><td><strong>Bidders Evaluated:</strong></td><td>{len(evaluations)}</td></tr>
            <tr><td><strong>Evaluation Date:</strong></td><td>{datetime.now().strftime('%d %B %Y, %I:%M %p')}</td></tr>
            <tr><td><strong>System:</strong></td><td>TenderSight v2.0 (Live AI Evaluation)</td></tr>
        </table>
    </div>
    """, unsafe_allow_html=True)

    # Summary Table
    st.markdown("### 📊 Bidder Summary Matrix")

    header = "| Bidder | " + " | ".join([c.get("id", f"C{i}") for i, c in enumerate(criteria)]) + " | Overall |"
    sep = "|" + "---|" * (len(criteria) + 2)
    rows = []
    for name, ev in evaluations.items():
        verdicts_map = {v.get("criterion_id"): v.get("status", "?") for v in ev.get("verdicts", [])}
        cells = []
        for c in criteria:
            cid = c.get("id", "")
            s = verdicts_map.get(cid, "?")
            cells.append("✅" if s == "ELIGIBLE" else "❌" if s == "NOT_ELIGIBLE" else "⚠️")
        overall = ev["overall_status"]
        cells.append("✅ ELIGIBLE" if overall == "ELIGIBLE" else "❌ NOT ELIGIBLE" if overall == "NOT_ELIGIBLE" else "⚠️ REVIEW")
        rows.append(f"| {name} | " + " | ".join(cells) + " |")

    st.markdown("\n".join([header, sep] + rows))

    # Detailed Verdicts
    st.markdown("### 📝 Detailed Verdict Cards")
    for name, ev in evaluations.items():
        overall = ev["overall_status"]
        icon = "✅" if overall == "ELIGIBLE" else "❌" if overall == "NOT_ELIGIBLE" else "⚠️"
        with st.expander(f"{icon} {name} — {overall.replace('_', ' ')}", expanded=True):
            for v in ev.get("verdicts", []):
                status = v.get("status", "MANUAL_REVIEW")
                cid = v.get("criterion_id", "")
                ctext = v.get("criterion_text", "")[:80]
                conf = v.get("confidence", 0.5)
                reasoning = v.get("reasoning", "")
                review_reason = v.get("review_reason", "")
                status_icon = "✅" if status == "ELIGIBLE" else "❌" if status == "NOT_ELIGIBLE" else "⚠️"
                evidence_lines = ""
                for ev_item in v.get("evidence_used", []):
                    doc = ev_item.get("source_document", "Unknown")
                    val = ev_item.get("value", "N/A")
                    evidence_lines += f"\n    📄 {doc}: **{val}**"
                st.markdown(f"""
**{status_icon} {cid}** — {ctext}...
- **Verdict:** {status.replace('_', ' ')} (Confidence: {int(conf*100)}%)
- **Reasoning:** {reasoning}
{f'- **⚠️ Review Needed:** {review_reason}' if review_reason else ''}
- **Evidence:**{evidence_lines if evidence_lines else ' No evidence extracted'}
                """)
                st.divider()

    # Audit Trail
    st.markdown("### 🔒 Audit Trail")
    st.markdown(f"""
    <div class="eval-card" style="background:#f8fafc;">
        <table style="font-size:0.8rem;color:#475569;width:100%;">
            <tr><td><strong>Evaluation Engine:</strong></td><td>TenderSight v2.0</td></tr>
            <tr><td><strong>LLM Provider Chain:</strong></td><td>NVIDIA → Gemini → Groq (auto-fallback)</td></tr>
            <tr><td><strong>Evaluation Protocol:</strong></td><td>3-Pass (Deterministic → LLM Reasoning → LLM Reviewer)</td></tr>
            <tr><td><strong>Security:</strong></td><td>Prompt injection scan + Unicode sanitization</td></tr>
            <tr><td><strong>Total Evaluations:</strong></td><td>{len(evaluations)} bidders × {len(criteria)} criteria × 3 passes</td></tr>
            <tr><td><strong>Timestamp:</strong></td><td>{datetime.now().isoformat()}</td></tr>
            <tr><td><strong>Disclaimer:</strong></td><td>AI-assisted evaluation. All verdicts must be reviewed by the authorized procurement officer.</td></tr>
        </table>
    </div>
    """, unsafe_allow_html=True)

    # Downloads
    st.markdown("### 💾 Export")
    col_pdf, col_json = st.columns(2)
    with col_pdf:
        try:
            pdf_bytes = generate_pdf_report(criteria, evaluations)
            st.download_button(
                "📥 Download PDF Report",
                pdf_bytes,
                "TenderSight_Evaluation_Report.pdf",
                "application/pdf",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"PDF generation error: {e}")
    with col_json:
        report_data = {
            "tender_ref": "CRPF/CE/2025-26/BOP-CONSTR/047",
            "tender_title": "Construction of Border Outpost Buildings — CRPF",
            "evaluation_date": datetime.now().isoformat(),
            "criteria_count": len(criteria),
            "criteria": criteria,
            "evaluations": evaluations,
            "audit": {
                "provider_chain": "NVIDIA → Gemini → Groq",
                "protocol": "3-Pass (Deterministic + LLM Reasoning + LLM Reviewer)",
                "system": "TenderSight v2.0",
            }
        }
        st.download_button(
            "📥 Download Raw Data (JSON)",
            json.dumps(report_data, indent=2, default=str),
            "tendersight_evaluation_report.json",
            "application/json",
            use_container_width=True
        )
