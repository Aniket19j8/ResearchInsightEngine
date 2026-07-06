"""Phase 4 - Insight search: cited, semantic retrieval over approved insights."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from src import repository, retrieval

st.set_page_config(page_title="Insight Search", page_icon="🔎", layout="wide")
repository.init_db()

st.title("🔎 Insight Search")
st.caption("Find insights by meaning. Every result is grounded in a real quote and study.")

with st.expander("ℹ️ How to use this page"):
    st.markdown(
        "Search past insights **by meaning**, not just keywords. Type a plain-English "
        "question and click **Search**. Each result shows the insight, its theme and "
        "severity, a similarity score (higher = closer match), and the study it came "
        "from.\n\n"
        "*Example queries:* `What do learners say about onboarding?` · "
        "`mobile navigation problems` · `accessibility and captions`\n\n"
        "*Tip:* approve insights on the **Synthesis Review** page first, or there will "
        "be nothing to find."
    )

query = st.text_input(
    "Ask the repository", placeholder="What do learners say about onboarding?",
    help="Example: What do learners say about onboarding?",
)

if st.button("Search", type="primary") and query.strip():
    try:
        results = retrieval.search(query.strip(), top_k=5)
    except Exception as e:
        st.error(f"Search failed (is the repository populated?): {e}")
        results = []

    if not results:
        st.write("No matching insights yet. Approve some on the Synthesis Review page.")

    studies = {s["id"]: s for s in repository.list_studies()}
    for r in results:
        meta = r["metadata"]
        study = studies.get(meta.get("study_id"), {})
        with st.container(border=True):
            st.markdown(f"**{r['insight']}**")
            st.caption(
                f"Theme: {meta.get('theme', '?')} · Severity: {meta.get('severity', '?')} · "
                f"Source: {meta.get('source', '?')} · Similarity: {r['similarity']}"
            )
            if study:
                st.caption(f"From study: {study.get('title')} ({study.get('id')})")
