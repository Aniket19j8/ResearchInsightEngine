"""Study Report - one-click executive summary of a study's approved insights.

Synthesizes the approved insights into stakeholder-ready prose, plus a
breakdown by theme and severity. Great as a demo finale.
"""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from src import report_pdf, repository, synthesis

st.set_page_config(page_title="Study Report", page_icon="🧾", layout="wide")
repository.init_db()

st.title("🧾 Study Report")


with st.expander("ℹ️ How to use this page"):
    st.markdown(
        "1. **Pick a study** that already has approved insights.\n"
        "2. Click **Generate report** - the AI synthesizes the insights into a "
        "short executive summary, plus theme and severity breakdowns.\n"
        "3. **Download** the report as a PDF to share.\n\n"
        "*Tip:* approve insights on the **Synthesis Review** page first, or this "
        "report will be empty."
    )

studies = repository.list_studies()
if not studies:
    st.warning("Create a study and approve some insights first.")
    st.stop()

study = st.selectbox(
    "Study", studies, format_func=lambda s: f"{s['title']} ({s['id']})",
    help="Select the study to summarize.",
)
insights = repository.list_insights(study["id"])

st.metric("Approved insights", len(insights))

if st.button("Generate report", type="primary"):
    if not insights:
        st.warning("This study has no approved insights yet.")
    else:
        with st.spinner("Synthesizing report..."):
            result = synthesis.generate_study_report(study, insights)

        st.caption(f"Generated via **{result.get('source', '?')}**")
        st.subheader("Executive summary")
        st.write(result["summary"])

        theme_counts = Counter(i.get("theme") for i in insights)
        severity_counts = Counter(i.get("severity") for i in insights)

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("By theme")
            st.bar_chart(dict(theme_counts))
        with col2:
            st.subheader("By severity")
            st.bar_chart(dict(severity_counts))

        st.subheader("All insights")
        for i in insights:
            with st.container(border=True):
                st.markdown(f"**{i.get('insight')}**")
                st.caption(
                    f"Theme: {i.get('theme')} · Severity: {i.get('severity')} · "
                    f"Source: {i.get('source')}"
                )
                st.markdown(f"> {i.get('quote')}")

        # Build downloadable PDF report.
        pdf_bytes = report_pdf.build_study_report_pdf(study, insights, result["summary"])

        st.download_button(
            "⬇️ Download report (PDF)",
            data=pdf_bytes,
            file_name=f"study_report_{study['id']}.pdf",
            mime="application/pdf",
        )
