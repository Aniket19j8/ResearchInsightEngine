"""Phase 5 - Ops dashboard: efficiency, reuse, adoption, AI override rate."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import plotly.express as px
import streamlit as st

from src import metrics, repository

st.set_page_config(page_title="Ops Dashboard", page_icon="📊", layout="wide")
repository.init_db()

st.title("📊 Operations Dashboard")


with st.expander("ℹ️ How to read this page"):
    st.markdown(
        "These metrics track the system's impact. They update automatically as you "
        "create studies, approve insights, and run searches - there's nothing to "
        "enter here.\n\n"
        "- **Avg time-to-insight** - study creation to first approved insight.\n"
        "- **AI override rate** - how often you approved vs edited vs rejected AI "
        "suggestions (a rising override rate warns the AI layer is degrading).\n"
        "- **Est. hours saved** - an *estimate* based on an assumed manual baseline.\n\n"
        "Use **Export metrics to CSV** to feed a Tableau dashboard."
    )

ttv = metrics.time_to_insight()
override = metrics.override_rate()
reuse = metrics.insight_reuse()
adopt = metrics.adoption()
saved = metrics.hours_saved()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Avg time-to-insight (min)", ttv["avg_minutes"])
c2.metric("Studies / Insights", f"{adopt['studies']} / {adopt['insights']}")
c3.metric("Searches", reuse["total_searches"])
c4.metric("Est. hours saved", saved["estimated_hours_saved"])
st.caption(
    f"Hours saved is an *estimate*: {saved['assumption_min_per_transcript']} min "
    "assumed manual tagging per study. Replace with measured baselines in production."
)

st.divider()
st.subheader("AI override rate")
if override["total"] > 0:
    fig = px.pie(
        names=["Approved as-is", "Edited", "Rejected"],
        values=[override["approve"], override["edit"], override["reject"]],
        title="What humans did with AI suggestions",
    )
    st.plotly_chart(fig, use_container_width=True)
    
else:
    st.write("No review actions logged yet.")

st.divider()
if st.button("Export metrics to CSV (for Tableau)"):
    path = metrics.export_csv()
    st.success(f"Exported to {path}")
