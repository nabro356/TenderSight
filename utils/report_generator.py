"""
PDF Report Generator for TenderSight — styled like the compliance agent reports.
"""
import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.colors import HexColor


# ─── Colors ───
PRIMARY = HexColor("#1E40AF")
SECONDARY = HexColor("#3B82F6")
ELIGIBLE_COLOR = HexColor("#16a34a")
NOT_ELIGIBLE_COLOR = HexColor("#dc2626")
MANUAL_REVIEW_COLOR = HexColor("#d97706")
TEXT_PRIMARY = HexColor("#1E293B")
TEXT_SECONDARY = HexColor("#64748B")
TEXT_LIGHT = HexColor("#FFFFFF")
BG_WHITE = HexColor("#FFFFFF")
BG_LIGHT = HexColor("#F8FAFC")
TABLE_ROW_ALT = HexColor("#F1F5F9")
TABLE_BORDER = HexColor("#E2E8F0")

ELIGIBLE_BG = HexColor("#DCFCE7")
NOT_ELIGIBLE_BG = HexColor("#FEE2E2")
MANUAL_REVIEW_BG = HexColor("#FEF3C7")


def _get_status_color(status):
    if status == "ELIGIBLE":
        return ELIGIBLE_COLOR
    elif status == "NOT_ELIGIBLE":
        return NOT_ELIGIBLE_COLOR
    return MANUAL_REVIEW_COLOR


def _get_status_bg(status):
    if status == "ELIGIBLE":
        return ELIGIBLE_BG
    elif status == "NOT_ELIGIBLE":
        return NOT_ELIGIBLE_BG
    return MANUAL_REVIEW_BG


def generate_pdf_report(criteria, evaluations):
    """Generate a detailed PDF evaluation report. Returns bytes."""
    buf = io.BytesIO()

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        rightMargin=0.75*inch, leftMargin=0.75*inch,
        topMargin=0.85*inch, bottomMargin=0.85*inch
    )

    styles = getSampleStyleSheet()

    # Custom styles
    styles.add(ParagraphStyle('RTitle', parent=styles['Heading1'], fontSize=26,
        textColor=PRIMARY, spaceAfter=10, alignment=TA_CENTER, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle('RSubtitle', parent=styles['Normal'], fontSize=12,
        textColor=TEXT_SECONDARY, spaceAfter=20, alignment=TA_CENTER))
    styles.add(ParagraphStyle('RSection', parent=styles['Heading2'], fontSize=15,
        textColor=PRIMARY, spaceBefore=18, spaceAfter=8))
    styles.add(ParagraphStyle('RSubsection', parent=styles['Heading3'], fontSize=12,
        textColor=SECONDARY, spaceBefore=12, spaceAfter=6))
    styles.add(ParagraphStyle('RBody', parent=styles['Normal'], fontSize=9.5,
        textColor=TEXT_PRIMARY, spaceAfter=6, leading=13))
    styles.add(ParagraphStyle('RSmall', parent=styles['Normal'], fontSize=8,
        textColor=TEXT_SECONDARY, leading=11))
    styles.add(ParagraphStyle('RCell', parent=styles['Normal'], fontSize=8.5,
        textColor=TEXT_PRIMARY, leading=11))

    def _page_template(canvas, doc):
        canvas.saveState()
        w, h = A4
        canvas.setFillColor(PRIMARY)
        canvas.rect(0, h - 50, w, 50, fill=True, stroke=False)
        canvas.rect(0, 0, w, 40, fill=True, stroke=False)
        canvas.setFillColor(TEXT_LIGHT)
        canvas.setFont('Helvetica', 8)
        canvas.drawString(0.5*inch, 14, "TenderSight v1.0 - CRPF Tender Evaluation")
        canvas.drawRightString(w - 0.5*inch, 14, f"Page {canvas.getPageNumber()}")
        canvas.restoreState()

    def _base_table_style():
        return TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
            ('TEXTCOLOR', (0, 0), (-1, 0), TEXT_LIGHT),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8.5),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (0, 0), (-1, -1), 1.5, PRIMARY),
            ('LINEBELOW', (0, 0), (-1, 0), 2, PRIMARY),
            ('INNERGRID', (0, 1), (-1, -1), 0.5, TABLE_BORDER),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [BG_WHITE, TABLE_ROW_ALT]),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ])

    story = []

    # ═══ TITLE PAGE ═══
    story.append(Spacer(1, 1.2*inch))
    story.append(Paragraph("TENDER EVALUATION REPORT", styles['RTitle']))
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph("AI-Powered Eligibility Analysis", styles['RSubtitle']))
    story.append(Spacer(1, 0.3*inch))
    story.append(HRFlowable(width="50%", color=PRIMARY, thickness=2))
    story.append(Spacer(1, 0.4*inch))

    # Tender info table
    info_data = [
        ['Tender Reference', 'CRPF/CE/2025-26/BOP-CONSTR/047'],
        ['Subject', 'Construction of Border Outpost Buildings - Rajasthan Sector'],
        ['Issuing Authority', 'Central Reserve Police Force (CRPF)'],
        ['Estimated Cost', 'Rs. 12,00,00,000 (Twelve Crore)'],
        ['Criteria Evaluated', str(len(criteria))],
        ['Bidders Evaluated', str(len(evaluations))],
        ['Evaluation Date', datetime.now().strftime('%d %B %Y, %I:%M %p')],
        ['System', 'TenderSight v1.0 (AI-Assisted Evaluation)'],
    ]
    info_table = Table(info_data, colWidths=[2.2*inch, 4*inch])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), PRIMARY),
        ('TEXTCOLOR', (1, 0), (1, -1), TEXT_PRIMARY),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, TABLE_BORDER),
    ]))
    story.append(info_table)

    story.append(Spacer(1, 0.5*inch))
    story.append(HRFlowable(width="50%", color=PRIMARY, thickness=2))
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph(
        f"Generated on {datetime.now().strftime('%B %d, %Y at %H:%M')}",
        styles['RSubtitle']
    ))
    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph(
        "<i>This report is AI-assisted. All verdicts must be reviewed by the authorized procurement officer.</i>",
        ParagraphStyle('Disclaimer', parent=styles['Normal'], fontSize=9,
            textColor=TEXT_SECONDARY, alignment=TA_CENTER)
    ))
    story.append(PageBreak())

    # ═══ SUMMARY MATRIX ═══
    story.append(Paragraph("Evaluation Summary", styles['RSection']))

    eligible = sum(1 for e in evaluations.values() if e["overall_status"] == "ELIGIBLE")
    not_elig = sum(1 for e in evaluations.values() if e["overall_status"] == "NOT_ELIGIBLE")
    manual = sum(1 for e in evaluations.values() if e["overall_status"] == "MANUAL_REVIEW")

    summary_data = [
        ['Metric', 'Count'],
        ['Total Bidders', str(len(evaluations))],
        ['Eligible', str(eligible)],
        ['Not Eligible', str(not_elig)],
        ['Manual Review Required', str(manual)],
        ['Total Criteria', str(len(criteria))],
        ['Total Evaluations (Bidders x Criteria x 3 Passes)', str(len(evaluations) * len(criteria) * 3)],
    ]
    summary_table = Table(summary_data, colWidths=[4*inch, 2*inch])
    st = _base_table_style()
    st.add('TEXTCOLOR', (1, 2), (1, 2), ELIGIBLE_COLOR)
    st.add('TEXTCOLOR', (1, 3), (1, 3), NOT_ELIGIBLE_COLOR)
    st.add('TEXTCOLOR', (1, 4), (1, 4), MANUAL_REVIEW_COLOR)
    st.add('FONTNAME', (1, 2), (1, 4), 'Helvetica-Bold')
    summary_table.setStyle(st)
    story.append(summary_table)
    story.append(Spacer(1, 0.3*inch))

    # Bidder summary matrix
    story.append(Paragraph("Bidder x Criteria Matrix", styles['RSubsection']))

    header = ['Bidder'] + [c.get("id", "") for c in criteria] + ['Overall']
    matrix_data = [header]
    for name, ev in evaluations.items():
        verdicts_map = {v.get("criterion_id"): v.get("status", "?") for v in ev.get("verdicts", [])}
        row = [Paragraph(name, styles['RCell'])]
        for c in criteria:
            s = verdicts_map.get(c.get("id", ""), "?")
            if s == "ELIGIBLE":
                row.append("PASS")
            elif s == "NOT_ELIGIBLE":
                row.append("FAIL")
            else:
                row.append("REVIEW")
        overall = ev["overall_status"].replace("_", " ")
        row.append(Paragraph(f"<b>{overall}</b>", styles['RCell']))
        matrix_data.append(row)

    ncols = len(criteria) + 2
    col_ws = [1.8*inch] + [0.55*inch]*len(criteria) + [1.0*inch]
    matrix_table = Table(matrix_data, colWidths=col_ws)
    mst = _base_table_style()
    mst.add('ALIGN', (1, 1), (-2, -1), 'CENTER')
    # Color-code PASS/FAIL/REVIEW cells
    for row_idx in range(1, len(matrix_data)):
        for col_idx in range(1, len(matrix_data[row_idx])):
            cell_val = matrix_data[row_idx][col_idx]
            if isinstance(cell_val, str):
                if cell_val == "PASS":
                    mst.add('TEXTCOLOR', (col_idx, row_idx), (col_idx, row_idx), ELIGIBLE_COLOR)
                    mst.add('FONTNAME', (col_idx, row_idx), (col_idx, row_idx), 'Helvetica-Bold')
                elif cell_val == "FAIL":
                    mst.add('TEXTCOLOR', (col_idx, row_idx), (col_idx, row_idx), NOT_ELIGIBLE_COLOR)
                    mst.add('FONTNAME', (col_idx, row_idx), (col_idx, row_idx), 'Helvetica-Bold')
                elif cell_val == "REVIEW":
                    mst.add('TEXTCOLOR', (col_idx, row_idx), (col_idx, row_idx), MANUAL_REVIEW_COLOR)
                    mst.add('FONTNAME', (col_idx, row_idx), (col_idx, row_idx), 'Helvetica-Bold')
    matrix_table.setStyle(mst)
    story.append(matrix_table)
    story.append(PageBreak())

    # ═══ DETAILED BIDDER REPORTS ═══
    for name, ev in evaluations.items():
        overall = ev["overall_status"]
        status_label = overall.replace("_", " ")
        sc = _get_status_color(overall)

        story.append(Paragraph(f"Bidder: {ev.get('bidder_name', name)}", styles['RSection']))

        # Overall status card
        status_data = [
            [Paragraph(f"<b>Overall Verdict: {status_label}</b>", ParagraphStyle(
                'SC', parent=styles['Normal'], fontSize=12, textColor=TEXT_LIGHT, fontName='Helvetica-Bold'
            )), ''],
        ]
        status_table = Table(status_data, colWidths=[6.2*inch, 0.1*inch])
        status_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), sc),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ]))
        story.append(status_table)
        story.append(Spacer(1, 0.15*inch))

        # Stats
        story.append(Paragraph(
            f"[PASS] {ev['eligible_count']} Eligible  |  [FAIL] {ev['not_eligible_count']} Not Eligible  |  [REVIEW] {ev['manual_review_count']} Manual Review",
            styles['RBody']
        ))
        story.append(Spacer(1, 0.1*inch))

        # Each criterion verdict
        for v in ev.get("verdicts", []):
            vstatus = v.get("status", "MANUAL_REVIEW")
            vcolor = _get_status_color(vstatus)
            vbg = _get_status_bg(vstatus)
            conf = v.get("confidence", 0.5)
            cid = v.get("criterion_id", "")
            ctype = v.get("criterion_type", "")

            # Verdict card header
            header_style = ParagraphStyle('VH', parent=styles['Normal'], fontSize=10,
                textColor=TEXT_LIGHT, fontName='Helvetica-Bold')
            hdr_text = f"[{vstatus.replace('_',' ')}] {cid} - {ctype} (Confidence: {int(conf*100)}%)"

            card_data = [
                [Paragraph(hdr_text, header_style), ''],
                ['Criterion', Paragraph(str(v.get('criterion_text', ''))[:200], styles['RCell'])],
                ['Reasoning', Paragraph(str(v.get('reasoning', '')), styles['RCell'])],
            ]

            # Add review reason if present
            if v.get("review_reason"):
                card_data.append(['[!] Review Needed', Paragraph(str(v['review_reason']), styles['RCell'])])

            # Add evidence
            for ei, ev_item in enumerate(v.get("evidence_used", [])):
                doc_name = ev_item.get("source_document", "Unknown")
                val = ev_item.get("value", "N/A")
                excerpt = str(ev_item.get("raw_excerpt", ""))[:180]
                ev_text = f"<b>{doc_name}</b>: {val}<br/><i>{excerpt}</i>"
                label = "Evidence" if ei == 0 else ""
                card_data.append([label, Paragraph(ev_text, styles['RCell'])])

            card_table = Table(card_data, colWidths=[1.3*inch, 5.0*inch])
            card_style = TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), vcolor),
                ('TEXTCOLOR', (0, 0), (-1, 0), TEXT_LIGHT),
                ('SPAN', (0, 0), (-1, 0)),
                ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 1), (0, -1), 8.5),
                ('TEXTCOLOR', (0, 1), (0, -1), SECONDARY),
                ('BACKGROUND', (0, 1), (0, -1), BG_LIGHT),
                ('BACKGROUND', (1, 1), (1, -1), BG_WHITE),
                ('BOX', (0, 0), (-1, -1), 1.5, vcolor),
                ('LINEBELOW', (0, 0), (-1, 0), 2, vcolor),
                ('INNERGRID', (0, 1), (-1, -1), 0.5, TABLE_BORDER),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 7),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ])
            card_table.setStyle(card_style)
            story.append(card_table)
            story.append(Spacer(1, 0.15*inch))

        story.append(PageBreak())

    # ═══ ANOMALY DETECTION ═══
    anomaly_bidders = [b for b, ev in evaluations.items() if ev.get("anomaly_flag")]
    if anomaly_bidders:
        story.append(Paragraph("Financial Anomaly & Risk Analysis", styles['RSection']))
        story.append(Paragraph(
            "The following bidders were flagged by the statistical anomaly detection engine due to highly abnormal financial bids compared to the tender median.",
            styles['RBody']
        ))
        story.append(Spacer(1, 0.1*inch))
        
        for b in anomaly_bidders:
            reason = evaluations[b].get("anomaly_reason", "Abnormal Bid")
            story.append(Paragraph(f"<b>🚨 {b}</b>: {reason}", styles['RBody']))
            story.append(Spacer(1, 0.05*inch))
            
        story.append(Spacer(1, 0.2*inch))
        story.append(PageBreak())

    # ═══ AUDIT TRAIL ═══
    story.append(Paragraph("Audit Trail", styles['RSection']))
    audit_data = [
        ['Parameter', 'Value'],
        ['Evaluation Engine', 'TenderSight v1.0'],
        ['LLM Model', 'Sovereign LLM (On-Premise, NVIDIA Inference)'],
        ['Evaluation Protocol', '3-Pass (Deterministic -> LLM Reasoning -> LLM Reviewer)'],
        ['Evidence Knowledge Graph', 'Neo4j (append-only, versioned)'],
        ['Total LLM Calls', str(len(evaluations) * len(criteria) * 3)],
        ['Timestamp', datetime.now().isoformat()],
        ['Data Sovereignty', 'All processing on-premise; no data sent to external APIs'],
    ]
    audit_table = Table(audit_data, colWidths=[2.5*inch, 3.8*inch])
    audit_table.setStyle(_base_table_style())
    story.append(audit_table)
    story.append(Spacer(1, 0.3*inch))

    story.append(Paragraph("Disclaimer", styles['RSubsection']))
    story.append(Paragraph(
        "This is an AI-assisted evaluation report generated by TenderSight. All verdicts are preliminary "
        "and must be reviewed and approved by the authorized CRPF procurement officer before being treated "
        "as final. The system is designed to assist, not replace, human judgment. Cases marked as "
        "MANUAL_REVIEW require specific human attention before a decision can be made.",
        styles['RBody']
    ))

    doc.build(story, onFirstPage=_page_template, onLaterPages=_page_template)
    buf.seek(0)
    return buf.getvalue()
