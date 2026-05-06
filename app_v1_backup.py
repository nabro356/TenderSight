"""
TenderSight v2.0 — AI-Powered Tender Evaluation
Streamlit App — New Flow: Tender → Add Bidders → Evaluate → Report
"""
import streamlit as st
import json, time, io
from pathlib import Path
from datetime import datetime
from agents.ingestion_agent import ingest_document
from agents.security_agent import check_security
from agents.criteria_agent import extract_criteria
from agents.judge_agent import evaluate_bidder
from agents.chat_agent import chat_about_report
from utils.report_generator import generate_pdf_report
from config import NVIDIA_API_KEY, SAMPLE_DATA_DIR

st.set_page_config(page_title="TenderSight", page_icon="⚖️", layout="wide", initial_sidebar_state="expanded")

css_path = Path(__file__).parent / "assets" / "style.css"
if css_path.exists():
    st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)

st.markdown("""<style>
.clean-card{background:#fff;border:1px solid #e2e8f0;border-radius:16px;padding:1.5rem;margin-bottom:1rem;box-shadow:0 1px 3px rgba(0,0,0,.04);transition:box-shadow .2s}
.clean-card:hover{box-shadow:0 4px 12px rgba(0,0,0,.08)}
.badge-sm{padding:2px 8px;border-radius:6px;font-size:.72rem;font-weight:700;display:inline-block}
.badge-eligible{background:#dcfce7;color:#166534}.badge-not-eligible{background:#fee2e2;color:#991b1b}.badge-review{background:#fef3c7;color:#854d0e}
.metric-row{display:flex;gap:1rem;margin-bottom:1.5rem}
.metric-card{flex:1;background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:1.25rem;text-align:center}
.metric-card .number{font-size:2rem;font-weight:800;line-height:1}.metric-card .label{font-size:.75rem;color:#64748b;text-transform:uppercase;font-weight:600;margin-top:.25rem}
.bidder-input-card{background:#f8fafc;border:2px dashed #cbd5e1;border-radius:16px;padding:1.5rem;margin-bottom:1rem}
</style>""", unsafe_allow_html=True)

def init_state():
    for k, v in {"step":1,"api_key":NVIDIA_API_KEY,"tender_text":"","criteria":[],"bidders":{},"evaluations":{},"chat_history":[]}.items():
        if k not in st.session_state: st.session_state[k] = v
init_state()

def badge(s):
    if s=="ELIGIBLE": return '<span class="badge-sm badge-eligible">ELIGIBLE</span>'
    if s=="NOT_ELIGIBLE": return '<span class="badge-sm badge-not-eligible">NOT ELIGIBLE</span>'
    return '<span class="badge-sm badge-review">REVIEW</span>'

def render_hero():
    st.markdown("""<div class="hero-header"><h1>⚖️ TenderSight</h1><p>AI-Powered Tender Evaluation for CRPF Government Procurement</p></div>""", unsafe_allow_html=True)

def render_progress():
    steps=[("📄","Tender"),("📁","Bidders"),("⚖️","Results")]
    cur=st.session_state.step
    items=""
    for i,(ic,lb) in enumerate(steps,1):
        cls="completed" if i<cur else ("active" if i==cur else "")
        num="✓" if i<cur else str(i)
        items+=f'<div class="step-item {cls}"><div class="step-number">{num}</div><span>{ic} {lb}</span></div>'
    st.markdown(f'<div class="step-progress">{items}</div>',unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### ⚙️ Configuration")
    ak=st.text_input("API Key",value=st.session_state.api_key,type="password")
    if ak: st.session_state.api_key=ak
    st.divider()
    if st.button("🔄 Reset",use_container_width=True):
        for k in list(st.session_state.keys()): del st.session_state[k]
        init_state(); st.rerun()

render_hero(); render_progress()

# ═══ STEP 1: Tender Document ═══
if st.session_state.step==1:
    st.markdown("## 📄 Step 1: Analyze Tender Document")
    c1,c2=st.columns([3,1])
    with c1: uploaded=st.file_uploader("Upload Tender (.txt, .pdf)",type=["txt","pdf"],key="tu")
    with c2:
        st.markdown("<br>",unsafe_allow_html=True)
        if st.button("📋 Sample Tender",use_container_width=True):
            p=SAMPLE_DATA_DIR/"tender.txt"
            if p.exists(): st.session_state.tender_text=p.read_text(encoding="utf-8"); st.rerun()
    if uploaded:
        with st.spinner("Processing..."): r=ingest_document(uploaded.read(),uploaded.name,api_key=st.session_state.api_key); st.session_state.tender_text=r["raw_text"]
        st.rerun()
    if st.session_state.tender_text:
        with st.expander("📖 Document Preview",expanded=False): st.text(st.session_state.tender_text[:2000])
        if st.button("🔍 Extract Eligibility Criteria",use_container_width=True,type="primary"):
            status=st.empty()
            with st.spinner("AI extracting criteria..."):
                try:
                    cr=extract_criteria(st.session_state.tender_text,api_key=st.session_state.api_key,progress_callback=lambda m:status.markdown(f"**{m}**"))
                    st.session_state.criteria=cr; st.session_state.step=2; st.rerun()
                except Exception as e: st.error(f"❌ {e}")
    else: st.info("💡 Click **Sample Tender** to load a CRPF construction tender.")

# ═══ STEP 2: Add Bidders + Evaluate ═══
elif st.session_state.step==2:
    st.markdown("## 📁 Step 2: Add Bidders & Evaluate")

    # Show extracted criteria in neat cards
    type_colors={"Financial":"#3b82f6","Experience":"#10b981","Compliance":"#f59e0b","Technical":"#8b5cf6"}
    type_icons={"Financial":"💰","Experience":"🏗️","Compliance":"📋","Technical":"⚙️"}
    with st.expander(f"📋 {len(st.session_state.criteria)} Eligibility Criteria Extracted",expanded=False):
        for c in st.session_state.criteria:
            cid=c.get("id","?"); ctype=c.get("type","General"); color=type_colors.get(ctype,"#64748b"); icon=type_icons.get(ctype,"📌")
            mandatory="✅ Mandatory" if c.get("mandatory",True) else "Optional"
            sub_html=""
            for sc in c.get("sub_conditions",[]):
                parts=[f'<code>{sc.get("parameter") or ""}</code>' if sc.get("parameter") else "",sc.get("operator") or "",f'<strong>{sc.get("threshold") or ""}</strong>' if sc.get("threshold") else "",sc.get("unit") or ""]
                desc=" ".join(p for p in parts if p)
                if desc.strip(): sub_html+=f'<div style="font-size:.8rem;color:#475569;padding:2px 0">• {desc}</div>'
            st.markdown(f"""<div class="clean-card" style="border-left:4px solid {color}"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.5rem"><div><span style="font-size:1.1rem">{icon}</span> <span style="font-weight:700;color:#1e293b">{cid}</span> <span class="badge-sm" style="background:{color}20;color:{color}">{ctype}</span></div><div style="font-size:.75rem;color:#94a3b8">{mandatory}</div></div><div style="color:#334155;font-size:.88rem;line-height:1.5">{c.get("text","")}</div>{f'<div style="margin-top:.5rem;padding-top:.5rem;border-top:1px solid #f1f5f9">{sub_html}</div>' if sub_html else ""}</div>""",unsafe_allow_html=True)

    st.divider()

    # Add Bidder Interface
    st.markdown("### ➕ Add Bidders")
    st.markdown("Add each bidder with a name and their submission documents.")

    # Sample bidders button
    c1,c2=st.columns([3,1])
    with c2:
        if st.button("📋 Load Sample Bidders",use_container_width=True):
            d=SAMPLE_DATA_DIR/"bidders"
            if d.exists():
                for f in sorted(d.glob("*.txt")): st.session_state.bidders[f.stem.replace("_"," ").title()]=f.read_text(encoding="utf-8")
                st.rerun()

    # Manual bidder add
    with st.container():
        col_name,col_file,col_btn=st.columns([2,3,1])
        with col_name: bname=st.text_input("Bidder Name",placeholder="e.g. Bharat Constructions",key="bname_input",label_visibility="collapsed")
        with col_file: bfile=st.file_uploader("Upload",type=["txt","pdf"],key="bfile_input",label_visibility="collapsed")
        with col_btn:
            if st.button("➕ Add",use_container_width=True,type="secondary"):
                if bname and bfile:
                    with st.spinner(f"Processing {bname}..."):
                        r=ingest_document(bfile.read(),bfile.name,api_key=st.session_state.api_key)
                        st.session_state.bidders[bname]=r["raw_text"]
                    st.rerun()
                elif bname and not bfile: st.warning("Upload a document for this bidder")
                else: st.warning("Enter a bidder name")

    # Show added bidders
    if st.session_state.bidders:
        st.markdown(f"### 🏢 {len(st.session_state.bidders)} Bidders Added")
        for i,name in enumerate(st.session_state.bidders):
            c1,c2=st.columns([5,1])
            with c1: st.markdown(f"**{i+1}.** 🏢 {name}")
            with c2:
                if st.button("🗑️",key=f"del_{i}"):
                    del st.session_state.bidders[name]; st.rerun()

        st.divider()

        # Evaluate button
        if not st.session_state.evaluations:
            if st.button("🚀 Evaluate All Bidders",use_container_width=True,type="primary"):
                progress=st.progress(0); status_text=st.empty(); detail_text=st.empty()
                names=list(st.session_state.bidders.keys())
                for idx,name in enumerate(names):
                    status_text.markdown(f"**⚖️ Evaluating [{idx+1}/{len(names)}]: {name}**")
                    try:
                        detail_text.markdown("🛡️ Security scan...")
                        security=check_security(st.session_state.bidders[name],filename=name)
                        detail_text.markdown(f"🧠 Analyzing {name}'s submission...")
                        evaluation=evaluate_bidder(
                            st.session_state.criteria,[],name,
                            api_key=st.session_state.api_key,progress_callback=lambda m:detail_text.markdown(m))
                        evaluation["security_report"]=security
                        st.session_state.evaluations[name]=evaluation
                    except Exception as e:
                        st.error(f"❌ {name}: {e}")
                        st.session_state.evaluations[name]={"bidder_name":name,"overall_status":"MANUAL_REVIEW","verdicts":[],"eligible_count":0,"not_eligible_count":0,"manual_review_count":len(st.session_state.criteria),"error":str(e)}
                    progress.progress((idx+1)/len(names))
                status_text.markdown("**✅ All evaluations complete!**"); detail_text.empty()
                time.sleep(1); st.session_state.step=3; st.rerun()

        # If already evaluated, show results inline
        if st.session_state.evaluations:
            st.session_state.step=3; st.rerun()

# ═══ STEP 3: Results + Charts + Report + Chatbot ═══
elif st.session_state.step==3:
    st.markdown("## ⚖️ Evaluation Results")
    evs=st.session_state.evaluations; criteria=st.session_state.criteria
    eligible=sum(1 for e in evs.values() if e["overall_status"]=="ELIGIBLE")
    not_elig=sum(1 for e in evs.values() if e["overall_status"]=="NOT_ELIGIBLE")
    review=sum(1 for e in evs.values() if e["overall_status"]=="MANUAL_REVIEW")

    # Metrics
    st.markdown(f"""<div class="metric-row">
        <div class="metric-card"><div class="number" style="color:#1e40af">{len(evs)}</div><div class="label">Total</div></div>
        <div class="metric-card"><div class="number" style="color:#16a34a">{eligible}</div><div class="label">Eligible</div></div>
        <div class="metric-card"><div class="number" style="color:#dc2626">{not_elig}</div><div class="label">Not Eligible</div></div>
        <div class="metric-card"><div class="number" style="color:#d97706">{review}</div><div class="label">Review</div></div>
    </div>""",unsafe_allow_html=True)

    # ─── Comparison Bar Chart ───
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np

        bidder_names=list(evs.keys())
        crit_ids=[str(c.get("id","")) for c in criteria]

        if bidder_names and crit_ids:
            # Grouped bar chart
            fig,ax=plt.subplots(figsize=(max(10,len(crit_ids)*1.5),5))
            fig.patch.set_facecolor("#ffffff")
            ax.set_facecolor("#f8fafc")
            x=np.arange(len(crit_ids)); width=0.8/max(len(bidder_names),1)
            colors=["#3b82f6","#10b981","#f59e0b","#ef4444","#8b5cf6","#06b6d4"]
            for i,name in enumerate(bidder_names):
                vm={str(v.get("criterion_id","")): float(v.get("confidence",0.5)) for v in evs[name].get("verdicts",[])}
                vals=[vm.get(cid,0) for cid in crit_ids]
                bars=ax.bar(x+i*width-0.4+width/2,vals,width*0.9,label=name[:20],color=colors[i%len(colors)],edgecolor="white",linewidth=0.5,alpha=0.85)
                for bar,val in zip(bars,vals):
                    if val>0: ax.text(bar.get_x()+bar.get_width()/2,bar.get_height()+0.02,f"{val:.0%}",ha="center",va="bottom",fontsize=7,color="#475569",fontweight="bold")
            ax.set_xticks(x); ax.set_xticklabels(crit_ids,fontsize=9,fontweight="bold",color="#334155")
            ax.set_ylim(0,1.15); ax.set_ylabel("Confidence",fontsize=10,color="#64748b")
            ax.set_title("Confidence by Criterion",fontsize=13,fontweight="bold",color="#1e293b",pad=12)
            ax.legend(fontsize=8,frameon=True,facecolor="white",edgecolor="#e2e8f0",loc="upper right")
            ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
            ax.spines["left"].set_color("#e2e8f0"); ax.spines["bottom"].set_color("#e2e8f0")
            ax.axhline(y=0.7,color="#dc2626",linewidth=1,linestyle="--",alpha=0.5,label="Review threshold")
            plt.tight_layout()
            buf=io.BytesIO(); fig.savefig(buf,format="png",dpi=150,bbox_inches="tight",facecolor="#fff"); buf.seek(0); plt.close(fig)
            st.image(buf,use_container_width=True)

            # Verdict scorecard (horizontal stacked bar)
            fig2,ax2=plt.subplots(figsize=(10,max(2,len(bidder_names)*0.8)))
            fig2.patch.set_facecolor("#ffffff")
            for i,name in enumerate(bidder_names):
                e=evs[name]; total=max(e.get("eligible_count",0)+e.get("not_eligible_count",0)+e.get("manual_review_count",0),1)
                elig_pct=e.get("eligible_count",0)/total; fail_pct=e.get("not_eligible_count",0)/total; rev_pct=e.get("manual_review_count",0)/total
                ax2.barh(i,elig_pct,color="#16a34a",height=0.5,label="Eligible" if i==0 else "")
                ax2.barh(i,rev_pct,left=elig_pct,color="#f59e0b",height=0.5,label="Review" if i==0 else "")
                ax2.barh(i,fail_pct,left=elig_pct+rev_pct,color="#dc2626",height=0.5,label="Not Eligible" if i==0 else "")
            ax2.set_yticks(range(len(bidder_names))); ax2.set_yticklabels([n[:25] for n in bidder_names],fontsize=10,color="#334155")
            ax2.set_xlim(0,1); ax2.set_xlabel("Proportion",fontsize=10,color="#64748b")
            ax2.set_title("Verdict Distribution",fontsize=13,fontweight="bold",color="#1e293b",pad=12)
            ax2.legend(fontsize=8,loc="lower right",frameon=True,facecolor="white",edgecolor="#e2e8f0")
            ax2.spines["top"].set_visible(False); ax2.spines["right"].set_visible(False)
            ax2.spines["left"].set_color("#e2e8f0"); ax2.spines["bottom"].set_color("#e2e8f0")
            plt.tight_layout()
            buf2=io.BytesIO(); fig2.savefig(buf2,format="png",dpi=150,bbox_inches="tight",facecolor="#fff"); buf2.seek(0); plt.close(fig2)
            st.image(buf2,use_container_width=True)
    except Exception as e:
        st.warning(f"Chart error: {e}")

    # ─── Bidder Result Cards ───
    st.markdown("### 📋 Detailed Results")
    for name,ev in evs.items():
        overall=ev["overall_status"]
        icon="✅" if overall=="ELIGIBLE" else "❌" if overall=="NOT_ELIGIBLE" else "⚠️"
        with st.expander(f"{icon} {name} — {overall.replace('_',' ')}",expanded=(overall!="ELIGIBLE")):
            if ev.get("error"): st.error(f"Error: {ev['error']}"); continue
            # Compact table
            for v in ev.get("verdicts",[]):
                s=v.get("status","MANUAL_REVIEW"); cid=v.get("criterion_id",""); conf=float(v.get("confidence",0.5))
                conf_color="#16a34a" if conf>=0.85 else "#d97706" if conf>=0.65 else "#dc2626"
                ev_val=str((v.get("evidence_used",[{}])[0].get("value","—") if v.get("evidence_used") else "—"))
                ev_src=str((v.get("evidence_used",[{}])[0].get("source_document","—") if v.get("evidence_used") else "—"))
                st.markdown(f"""<div style="display:flex;align-items:center;padding:.6rem 0;border-bottom:1px solid #f1f5f9;gap:.75rem;font-size:.88rem">
                    <div style="width:10px;height:10px;border-radius:50%;background:{'#16a34a' if s=='ELIGIBLE' else '#dc2626' if s=='NOT_ELIGIBLE' else '#d97706'};flex-shrink:0"></div>
                    <div style="font-weight:700;color:#475569;min-width:70px">{cid}</div>
                    <div style="flex:1;color:#64748b">{str(v.get('criterion_text',''))[:60]}</div>
                    {badge(s)}
                    <div style="font-size:.78rem;color:{conf_color};font-weight:700;min-width:40px;text-align:right">{conf:.0%}</div>
                </div>""",unsafe_allow_html=True)
            # Expandable reasoning
            for v in ev.get("verdicts",[]):
                if v.get("reasoning"):
                    with st.expander(f"📝 {v.get('criterion_id','')} — Detail",expanded=False):
                        st.markdown(f"**Reasoning:** {v['reasoning']}")
                        if v.get("evidence_used"):
                            for ei in v["evidence_used"]:
                                st.markdown(f"📄 **{str(ei.get('source_document','?'))}:** {str(ei.get('value','N/A'))}")

    # ─── Summary Matrix ───
    st.markdown("### 📊 Summary Matrix")
    header="| Bidder | "+" | ".join([str(c.get("id","")) for c in criteria])+" | Overall |"
    sep="|"+"---|"*(len(criteria)+2)
    rows=[]
    for name,ev in evs.items():
        vm={str(v.get("criterion_id","")): v.get("status","?") for v in ev.get("verdicts",[])}
        cells=["✅" if vm.get(str(c.get("id","")),"?")=="ELIGIBLE" else "❌" if vm.get(str(c.get("id","")),"?")=="NOT_ELIGIBLE" else "⚠️" for c in criteria]
        o=ev["overall_status"]; cells.append("✅" if o=="ELIGIBLE" else "❌" if o=="NOT_ELIGIBLE" else "⚠️")
        rows.append(f"| {name} | "+" | ".join(cells)+" |")
    st.markdown("\n".join([header,sep]+rows))

    # ─── Audit Trail ───
    st.markdown(f"""<div class="clean-card" style="font-size:.85rem;color:#475569">
        <strong>🔒 Audit:</strong> TenderSight v2.0 · LLM Fallback: NVIDIA→Gemini→Groq · Protocol: Evidence+Evaluation (batch) + Reviewer ·
        {len(evs)} bidders × {len(criteria)} criteria · {datetime.now().strftime('%d %B %Y, %I:%M %p')} ·
        <em style="color:#94a3b8">AI-assisted. All verdicts require procurement officer review.</em></div>""",unsafe_allow_html=True)

    # ─── Generate PDF Report ───
    st.markdown("### 💾 Export Report")
    c1,c2=st.columns(2)
    with c1:
        try:
            pdf=generate_pdf_report(criteria,evs)
            st.download_button("📥 Download PDF Report",pdf,"TenderSight_Report.pdf","application/pdf",use_container_width=True)
        except Exception as e: st.error(f"PDF error: {e}")
    with c2:
        data={"criteria":criteria,"evaluations":evs,"timestamp":datetime.now().isoformat(),"system":"TenderSight v2.0"}
        st.download_button("📥 Download JSON",json.dumps(data,indent=2,default=str),"tendersight_report.json","application/json",use_container_width=True)

    # ─── Chatbot ───
    st.divider()
    st.markdown("### 💬 Ask About This Report")
    if "chat_history" not in st.session_state: st.session_state.chat_history=[]
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])
    if not st.session_state.chat_history:
        suggestions=[]
        for name,ev in evs.items():
            if ev["overall_status"]=="MANUAL_REVIEW": suggestions.append(f"Why was {name} flagged for manual review?")
            elif ev["overall_status"]=="NOT_ELIGIBLE": suggestions.append(f"Why was {name} not eligible?")
        if len(evs)>1: suggestions.append("Compare all bidders and rank them")
        cols=st.columns(min(len(suggestions),3))
        for i,s in enumerate(suggestions[:3]):
            with cols[i]:
                if st.button(f"💡 {s[:45]}",key=f"sug_{i}",use_container_width=True):
                    st.session_state.chat_history.append({"role":"user","content":s})
                    with st.spinner("Thinking..."):
                        ans=chat_about_report(s,{"criteria":criteria,"evaluations":evs},api_key=st.session_state.api_key)
                    st.session_state.chat_history.append({"role":"assistant","content":ans}); st.rerun()
    uq=st.chat_input("Ask about the evaluation...")
    if uq:
        st.session_state.chat_history.append({"role":"user","content":uq})
        with st.chat_message("user"): st.markdown(uq)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                ans=chat_about_report(uq,{"criteria":criteria,"evaluations":evs},api_key=st.session_state.api_key)
            st.markdown(ans)
        st.session_state.chat_history.append({"role":"assistant","content":ans})
