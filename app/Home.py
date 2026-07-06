"""UX Research Insight Engine - Streamlit entry point.

Run from the project root:
    streamlit run app/Home.py
"""
import sys
from pathlib import Path

# Make the project root importable so `from src import ...` works.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from src import llm, repository

st.set_page_config(page_title="UX Research Insight Engine", page_icon="🧭", layout="wide")

repository.init_db()

st.title("UX Research Insight")


st.markdown(
    """
This tool turns raw interview transcripts, surveys, and documents into reusable, searchable research insights:

1. **Intake** - register a study.
2. **Synthesis (AI)** - the model proposes themes, verbatim quotes, and draft insights (PII is auto-redacted first).
3. **Human Review** - you approve / edit / reject every suggestion.
4. **Insight Search** - approved insights are embedded and searchable, with citations.
5. **Ops Dashboard** - time-to-insight, reuse, adoption, and the AI override rate.
6. **Governance** - the green / yellow / red AI-use policy.
7. **Document Analysis** - summarize uploaded docs or search research papers (arXiv).
8. **Study Report** - one-click executive summary of a study's insights.

Use the sidebar to move through the workflow. Each page has an
**"ℹ️ How to use this page"** expander at the top with examples.
    """
)

col1, col2, col3 = st.columns(3)
col1.metric("Studies", len(repository.list_studies()))
col2.metric("Approved insights", len(repository.list_insights()))
col3.metric("LLM status", "Live" if llm.is_live() else "Fallback mode")

if not llm.is_live():
    st.info(
        "No OpenAI key detected - the app runs in **keyword-fallback mode** so the "
        "workflow still works. Add `OPENAI_API_KEY` to a `.env` file to enable AI synthesis."
    )
