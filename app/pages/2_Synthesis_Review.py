"""Phase 2+3 - AI synthesis and the human review gate (the star page).

AI proposes; the human disposes. Only approved items reach the repository,
and every decision is written to the audit log.
"""
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from src import config, privacy, repository, retrieval, synthesis

st.set_page_config(page_title="Synthesis Review", page_icon="🔬", layout="wide")
repository.init_db()

st.title("🔬 Synthesis & Human Review")
st.caption("AI does the first pass - you own the final interpretation.")

with st.expander("ℹ️ How to use this page"):
    st.markdown(
        "1. **Pick the study** this transcript belongs to.\n"
        "2. **Choose a transcript** (a built-in sample) or paste your own.\n"
        "3. Click **Run AI synthesis** - the AI proposes themes, quotes, and "
        "draft insights. Any participant PII is automatically redacted first.\n"
        "4. For each suggestion, **Approve**, **edit then save**, or **Reject**. "
        "Only approved items enter the searchable repository.\n\n"
        "*Example transcript line:* `Learner: The signup was fine but the "
        "dashboard was empty and I didn't know where to start.`"
    )

studies = repository.list_studies()
if not studies:
    st.warning("Create a study first on the Intake page.")
    st.stop()

study_label = st.selectbox(
    "Study", studies, format_func=lambda s: f"{s['title']} ({s['id']})",
    help="Select which study this transcript belongs to.",
)
study_id = study_label["id"]

# --- Transcript input ------------------------------------------------------
transcript_files = sorted(config.TRANSCRIPTS_DIR.glob("*.txt"))
choices = ["(paste manually)"] + [f.name for f in transcript_files]
choice = st.selectbox("Transcript", choices)

if choice == "(paste manually)":
    transcript = st.text_area("Paste transcript", height=200)
else:
    transcript = (config.TRANSCRIPTS_DIR / choice).read_text(encoding="utf-8")
    st.text_area("Transcript", transcript, height=200, disabled=True)

if st.button("Run AI synthesis", type="primary") and transcript.strip():
    result = synthesis.synthesize(transcript)
    st.session_state["suggestions"] = result["items"]
    st.session_state["synthesis_source"] = result["source"]
    st.session_state["pii_report"] = result.get("pii_report", {})
    st.session_state["handled"] = {}

# --- Review the suggestions ------------------------------------------------
suggestions = st.session_state.get("suggestions", [])
if suggestions:
    source = st.session_state.get("synthesis_source", "")
    pii_report = st.session_state.get("pii_report", {})
    st.info(f"{len(suggestions)} suggestion(s) generated via **{source}**. "
            "Approve, edit, or reject each one.")
    if pii_report:
        st.warning("🔒 " + privacy.summarize_report(pii_report)
                   + " (PII removed before sending to the AI.)")

    themes = config.allowed_themes()
    severities = config.allowed_severities()
    handled = st.session_state.setdefault("handled", {})

    for i, item in enumerate(suggestions):
        if handled.get(i):
            st.success(f"Item {i + 1}: {handled[i]}")
            continue

        conf = float(item.get("confidence", 0.5))
        low = conf < config.LOW_CONFIDENCE_THRESHOLD
        flag = "🔴 LOW" if low else "🟢"
        with st.container(border=True):
            st.markdown(f"**Suggestion {i + 1}** — confidence {conf:.2f} {flag}")
            st.markdown(f"> {item['quote']}")

            c1, c2 = st.columns(2)
            theme = c1.selectbox(
                "Theme", themes,
                index=themes.index(item["theme"]) if item["theme"] in themes else 0,
                key=f"theme_{i}",
            )
            severity = c2.selectbox(
                "Severity", severities,
                index=severities.index(item.get("severity", "medium"))
                if item.get("severity") in severities else 1,
                key=f"sev_{i}",
            )
            insight_text = st.text_area(
                "Draft insight (editable)", item.get("draft_insight", ""), key=f"ins_{i}"
            )

            b1, b2, b3 = st.columns(3)
            approve = b1.button("✅ Approve", key=f"app_{i}")
            edit = b2.button("✏️ Save edited", key=f"edit_{i}")
            reject = b3.button("❌ Reject", key=f"rej_{i}")

            if approve or edit:
                edited = (
                    theme != item["theme"]
                    or severity != item.get("severity")
                    or insight_text.strip() != item.get("draft_insight", "").strip()
                )
                source_tag = "human_edited" if (edit or edited) else "ai_approved"
                insight_id = str(uuid.uuid4())[:12]

                repository.save_insight(
                    insight_id=insight_id, study_id=study_id, theme=theme,
                    quote=item["quote"], insight=insight_text.strip(),
                    severity=severity, confidence=conf, source=source_tag,
                )
                try:
                    retrieval.index_insight(
                        insight_id, insight_text.strip(),
                        {"study_id": study_id, "theme": theme,
                         "severity": severity, "source": source_tag},
                    )
                except Exception as e:  # indexing is best-effort for the demo
                    st.warning(f"Saved, but indexing failed: {e}")

                repository.log_action(
                    action="edit" if source_tag == "human_edited" else "approve",
                    ai_value=item,
                    human_value={"theme": theme, "severity": severity,
                                 "insight": insight_text.strip()},
                    insight_id=insight_id, study_id=study_id,
                )
                handled[i] = f"Saved as {source_tag}."
                st.rerun()

            if reject:
                repository.log_action(
                    action="reject", ai_value=item, human_value=None, study_id=study_id
                )
                handled[i] = "Rejected (not saved)."
                st.rerun()
