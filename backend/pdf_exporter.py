import io
from fpdf import FPDF
from typing import Dict, Any

def sanitize_text(text: Any) -> str:
    """Replaces non-latin1 unicode characters with clean ASCII strings to prevent FPDF errors."""
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)
    replacements = {
        "—": "-",
        "–": "-",
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
        "•": "*",
        "…": "...",
        "⚡": "[ATTACK]",
        "🔴": "[FLAGGED]",
        "🟢": "[CLEARED]",
        "🟡": "[WARNING]",
        "🕸️": "[GRAPH]",
        "📄": "[DOC]",
        "🔍": "[SEARCH]",
        "±": "+/-",
    }
    for orig, repl in replacements.items():
        text = text.replace(orig, repl)
    return text.encode("latin-1", errors="replace").decode("latin-1")

class VigilAuditPDF(FPDF):
    def header(self):
        # Top Institutional Header Bar
        self.set_fill_color(15, 23, 42)  # Slate 900
        self.rect(0, 0, 210, 14, style="F")
        self.set_xy(10, 3)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(255, 255, 255)
        self.cell(100, 8, sanitize_text("VIGIL AI GOVERNANCE | CONFIDENTIAL FORENSIC AUDIT REPORT"), align="L")
        self.set_xy(110, 3)
        self.cell(90, 8, sanitize_text("ISO/IEC 42001 COMPLIANT AUDIT TRAIL"), align="R")
        self.ln(14)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(100, 116, 139)  # Slate 500
        self.cell(0, 10, sanitize_text(f"Page {self.page_no()}/{{nb}} -- Vigil Autonomous Fraud Platform -- Confidential Legal Audit Document"), align="C")

def render_dossier_pdf(dossier_data: Dict[str, Any]) -> io.BytesIO:
    """
    Renders an institutional-grade Vigil Forensic Audit Report PDF binary stream buffer.
    """
    pdf = VigilAuditPDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    tx_id = sanitize_text(str(dossier_data.get("transaction_id", "N/A")))
    score = float(dossier_data.get("risk_score", dossier_data.get("catboost_score", 0.0)))
    verdict = sanitize_text(str(dossier_data.get("verdict", dossier_data.get("recommended_action", "PENDING_REVIEW"))))
    classification = sanitize_text(str(dossier_data.get("classification", "ANALYZED_TRANSACTION")))
    confidence = dossier_data.get("confidence_percentage", 95)
    exec_summary = sanitize_text(str(dossier_data.get("executive_analyst_summary", dossier_data.get("executive_summary", "No executive summary available."))))

    behavioral = sanitize_text(str(dossier_data.get("behavioral_diagnostics", "")))
    infrastructure = sanitize_text(str(dossier_data.get("network_infrastructure_forensics", "")))
    graph_syndicate = sanitize_text(str(dossier_data.get("graph_syndicate_assessment", dossier_data.get("graph_corroboration", ""))))
    mitigating_text = sanitize_text(str(dossier_data.get("mitigating_defense_factors", "")))
    remediation_list = dossier_data.get("remediation_action_plan", [])

    is_high_risk = score >= 0.70 or "DECLINE" in verdict or "FREEZE" in verdict

    # ==========================================
    # EXECUTIVE HEADER BLOCK
    # ==========================================
    pdf.set_fill_color(248, 250, 252)  # Slate 50
    pdf.rect(10, 20, 190, 32, style="F")
    pdf.set_draw_color(226, 232, 240)
    pdf.rect(10, 20, 190, 32, style="D")

    # Title inside box
    pdf.set_xy(15, 23)
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(110, 6, sanitize_text(f"Case ID: {tx_id}"))

    # Verdict Badge
    pdf.set_xy(125, 23)
    pdf.set_font("Helvetica", "B", 11)
    if is_high_risk:
        pdf.set_text_color(220, 38, 38)
        badge_text = f"VERDICT: {verdict}"
    elif score >= 0.40:
        pdf.set_text_color(217, 119, 6)
        badge_text = f"VERDICT: {verdict}"
    else:
        pdf.set_text_color(22, 163, 74)
        badge_text = f"VERDICT: {verdict}"
    pdf.cell(70, 6, sanitize_text(badge_text), align="R")

    # Second row inside box
    pdf.set_xy(15, 31)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(110, 5, sanitize_text(f"Classification: {classification.replace('_', ' ')}"))

    pdf.set_xy(125, 31)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(70, 5, sanitize_text(f"ML Score: {score:.3f} / 1.000"), align="R")

    # Third row inside box
    pdf.set_xy(15, 38)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(110, 5, sanitize_text(f"Evaluation Engine: CatBoost ML & TreeSHAP Reasoning"))

    pdf.set_xy(125, 38)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(70, 5, sanitize_text(f"Machine Confidence: {confidence}%"), align="R")

    pdf.set_xy(pdf.l_margin, 58)

    # ==========================================
    # SECTION 1: EXECUTIVE CASE NARRATIVE
    # ==========================================
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(pdf.epw, 7, sanitize_text("1. Executive Case Narrative"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(15, 23, 42)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)

    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_text_color(51, 65, 85)
    pdf.multi_cell(pdf.epw, 5, exec_summary, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # ==========================================
    # SECTION 2: QUANTITATIVE FEATURE BREAKDOWN (TABLE)
    # ==========================================
    drivers = dossier_data.get("explainability_drivers", [])
    if drivers:
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(pdf.epw, 7, sanitize_text("2. Quantitative Feature & SHAP Risk Breakdown"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(15, 23, 42)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(3)

        # Header Row
        pdf.set_font("Helvetica", "B", 8.5)
        pdf.set_fill_color(15, 23, 42)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(50, 6, sanitize_text(" Feature Name"), border=1, fill=True)
        pdf.cell(45, 6, sanitize_text(" Observed Value"), border=1, fill=True)
        pdf.cell(50, 6, sanitize_text(" Historical Baseline"), border=1, fill=True)
        pdf.cell(45, 6, sanitize_text(" SHAP Impact (+/-)"), border=1, fill=True, new_x="LMARGIN", new_y="NEXT")

        # Data Rows
        pdf.set_font("Helvetica", "", 8.5)
        pdf.set_text_color(30, 41, 59)
        for idx, drv in enumerate(drivers):
            fill_bg = (248, 250, 252) if idx % 2 == 1 else (255, 255, 255)
            pdf.set_fill_color(*fill_bg)

            if isinstance(drv, dict):
                feat = sanitize_text(str(drv.get("feature", "N/A")))
                val = sanitize_text(str(drv.get("value", "N/A")))
                base = sanitize_text(str(drv.get("baseline_value", "Historical Baseline")))
                shap_val = float(drv.get("shap_value", 0.0))
                impact_str = sanitize_text(drv.get("directional_impact", f"{shap_val:+.3f}"))
            else:
                feat = sanitize_text(str(drv))
                val = "N/A"
                base = "N/A"
                shap_val = 0.0
                impact_str = "0.000"

            pdf.cell(50, 6, f" {feat}", border=1, fill=True)
            pdf.cell(45, 6, f" {val}", border=1, fill=True)
            pdf.cell(50, 6, f" {base}", border=1, fill=True)

            if shap_val > 0:
                pdf.set_text_color(220, 38, 38)
            else:
                pdf.set_text_color(22, 163, 74)
            pdf.cell(45, 6, f" {impact_str}", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(30, 41, 59)

        pdf.ln(5)

    # ==========================================
    # SECTION 3: DUAL-COLUMN FORENSIC CASE FILE
    # ==========================================
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(pdf.epw, 7, sanitize_text("3. Dual-Column Forensic Case File (Prosecution vs. Defense)"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(15, 23, 42)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)

    # Sub-Section A: Prosecution / Incriminating Red Flags
    prosecution_list = dossier_data.get("prosecution_evidence", dossier_data.get("evidence_prosecution", []))
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(220, 38, 38)
    pdf.cell(pdf.epw, 6, sanitize_text(f"Sub-Section A: Prosecution Evidence / Incriminating Signals ({len(prosecution_list)})"), new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(30, 41, 59)
    if not prosecution_list:
        pdf.cell(pdf.epw, 5, sanitize_text("   * [CLEARED] Zero incriminating signals or fraud anomalies flagged."), new_x="LMARGIN", new_y="NEXT")
    else:
        for idx, item in enumerate(prosecution_list, 1):
            if isinstance(item, dict):
                title = sanitize_text(item.get("title", item.get("indicator", "Fraud Indicator")))
                detail = sanitize_text(item.get("description", item.get("observation", "")))
                severity = sanitize_text(str(item.get("severity", "HIGH")))
                impact = item.get("impact", None)
                impact_part = f" (Impact: +{impact:.3f})" if impact is not None and isinstance(impact, (int, float)) else ""
                text = f"   * [{severity}] {title}: {detail}{impact_part}"
            else:
                text = f"   * {sanitize_text(str(item))}"
            pdf.multi_cell(pdf.epw, 5, text, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # Sub-Section B: Defense / Mitigating Signals
    defense_list = dossier_data.get("defense_evidence", dossier_data.get("counter_evidence_defense", []))
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(22, 163, 74)
    pdf.cell(pdf.epw, 6, sanitize_text(f"Sub-Section B: Defense Counter-Evidence / Mitigating Signals ({len(defense_list)})"), new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(30, 41, 59)
    if not defense_list:
        pdf.cell(pdf.epw, 5, sanitize_text("   * [NO COUNTERWEIGHTS] No mitigating factors identified to counter risk score."), new_x="LMARGIN", new_y="NEXT")
    else:
        for idx, item in enumerate(defense_list, 1):
            if isinstance(item, dict):
                title = sanitize_text(item.get("title", item.get("indicator", "Mitigating Factor")))
                detail = sanitize_text(item.get("description", item.get("observation", "")))
                significance = sanitize_text(str(item.get("significance", "STRONG")))
                text = f"   * [{significance}] {title}: {detail}"
            else:
                text = f"   * {sanitize_text(str(item))}"
            pdf.multi_cell(pdf.epw, 5, text, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # ==========================================
    # SECTION 4: GRAPH & IDENTITY TOPOLOGY AUDIT
    # ==========================================
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(pdf.epw, 7, sanitize_text("4. Graph Topology & Identity Forensics Audit"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(15, 23, 42)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(51, 65, 85)

    if behavioral:
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.set_text_color(30, 41, 59)
        pdf.cell(pdf.epw, 5, sanitize_text("A) Behavioral & Velocity Diagnostics:"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(pdf.epw, 4.5, behavioral, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    if infrastructure:
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.set_text_color(30, 41, 59)
        pdf.cell(pdf.epw, 5, sanitize_text("B) Device & Infrastructure Forensics:"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(pdf.epw, 4.5, infrastructure, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    if graph_syndicate:
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.set_text_color(30, 41, 59)
        pdf.cell(pdf.epw, 5, sanitize_text("C) Graph Syndicate Traversal:"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(pdf.epw, 4.5, graph_syndicate, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    if mitigating_text and not defense_list:
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.set_text_color(30, 41, 59)
        pdf.cell(pdf.epw, 5, sanitize_text("D) Defense Evaluation Rationale:"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(pdf.epw, 4.5, mitigating_text, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    pdf.ln(3)

    # ==========================================
    # SECTION 5: RECOMMENDED ACTION PLAN & COMPLIANCE
    # ==========================================
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(pdf.epw, 7, sanitize_text("5. Recommended Action Plan & Compliance Protocol"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(15, 23, 42)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(30, 41, 59)

    if isinstance(remediation_list, list) and remediation_list:
        for rem in remediation_list:
            pdf.multi_cell(pdf.epw, 4.5, sanitize_text(str(rem)), new_x="LMARGIN", new_y="NEXT")
    elif isinstance(remediation_list, str) and remediation_list:
        pdf.multi_cell(pdf.epw, 4.5, sanitize_text(remediation_list), new_x="LMARGIN", new_y="NEXT")
    else:
        if is_high_risk:
            pdf.multi_cell(pdf.epw, 4.5, sanitize_text("1. Immediate Freeze: Freeze target user account and block outgoing wire transactions.\n2. Revoke OAuth Tokens: Blacklist originating IP and clear active device session tokens.\n3. Compliance Filing: File Suspicious Activity Report (SAR) documenting cross-account ring topology."), new_x="LMARGIN", new_y="NEXT")
        else:
            pdf.multi_cell(pdf.epw, 4.5, sanitize_text("1. Automated Release: Approve transaction settlement without user friction.\n2. Model Calibration: Update CatBoost online feature weights for trusted hardware GUID."), new_x="LMARGIN", new_y="NEXT")

    # Output BytesIO buffer
    pdf_buffer = io.BytesIO()
    pdf_bytes = pdf.output()
    pdf_buffer.write(pdf_bytes)
    pdf_buffer.seek(0)
    return pdf_buffer
