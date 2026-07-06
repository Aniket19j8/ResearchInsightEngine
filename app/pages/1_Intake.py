"""Phase 1 - Intake: standardized front door for new studies."""
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from src import repository

st.set_page_config(page_title="Intake", page_icon="📝")
repository.init_db()

st.title("📝 Study Intake")


with st.expander("ℹ️ How to use this page"):
    st.markdown(
        "Register a new research study - the standardized intake form so every "
        "study starts with the same structure. Fill in the form and click "
        "**Create study**. You'll attach transcripts to it on the next page.\n\n"
        "*Example:* Title `Onboarding Study`, question `What confuses new learners "
        "in their first session?`, method `interview`, persona `New learner`."
    )

with st.form("intake_form", clear_on_submit=True):
    st.caption("Give the study a short, recognizable name.")
    title = st.text_input("Study title", placeholder="Onboarding Study",
                          help="Example: Onboarding Study")
    st.caption("The single question this study is trying to answer.")
    research_question = st.text_area(
        "Research question", placeholder="What confuses new learners in their first session?",
        help="Example: What confuses new learners in their first session?",
    )
    method = st.selectbox("Method", ["interview", "usability test", "survey"],
                          help="How the data was collected.")
    product_area = st.text_input("Product area", placeholder="Onboarding",
                                 help="Example: Onboarding, Mobile experience, Checkout")
    persona = st.text_input("Persona", placeholder="New learner",
                            help="Example: New learner, Commute learner")
    submitted = st.form_submit_button("Create study")

if submitted:
    if not title.strip():
        st.error("A title is required.")
    else:
        study = repository.create_study(
            study_id=str(uuid.uuid4())[:8],
            title=title.strip(),
            research_question=research_question.strip(),
            method=method,
            product_area=product_area.strip(),
            persona=persona.strip(),
        )
        st.success(f"Created study '{title}' (id: {study['id']}).")

st.divider()
st.subheader("Existing studies")
studies = repository.list_studies()
if studies:
    st.dataframe(studies, use_container_width=True)
else:
    st.write("No studies yet.")
