"""Build a study report as PDF bytes for download."""
from __future__ import annotations

from fpdf import FPDF


def _safe(text: str) -> str:
    """FPDF core fonts are Latin-1; replace unsupported chars."""
    if not text:
        return ""
    return text.encode("latin-1", errors="replace").decode("latin-1")


class _ReportPDF(FPDF):
    def header(self) -> None:
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 10, _safe("UX Research Insight Engine - Study Report"), new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, _safe(f"Page {self.page_no()}"), align="C")


def _wrap(pdf: FPDF, text: str, h: float = 6) -> None:
    pdf.multi_cell(w=pdf.epw, h=h, text=_safe(text))


def build_study_report_pdf(study: dict, insights: list[dict], summary: str) -> bytes:
    """Return PDF file bytes for a study report."""
    pdf = _ReportPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    _wrap(pdf, study.get("title", "Study Report"), h=10)
    pdf.ln(4)

    pdf.set_font("Helvetica", "", 11)
    _wrap(pdf, f"Research question: {study.get('research_question', 'N/A')}")
    _wrap(pdf, f"Study ID: {study.get('id', '')}")
    _wrap(pdf, f"Approved insights: {len(insights)}")
    pdf.ln(6)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, _safe("Executive Summary"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    _wrap(pdf, summary)
    pdf.ln(6)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, _safe("Insights"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    for idx, ins in enumerate(insights, start=1):
        pdf.set_font("Helvetica", "B", 11)
        theme = ins.get("theme", "?")
        severity = ins.get("severity", "?")
        _wrap(pdf, f"{idx}. [{theme} / {severity}] {ins.get('insight', '')}")
        pdf.set_font("Helvetica", "I", 10)
        _wrap(pdf, f'   Quote: "{ins.get("quote", "")}"', h=5)
        pdf.set_font("Helvetica", "", 9)
        _wrap(pdf, f"   Source: {ins.get('source', '?')}", h=5)
        pdf.ln(4)

    return bytes(pdf.output())
