"""Phase 6 - Governance: render the AI-use policy inside the app."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

st.set_page_config(page_title="Governance", page_icon="🛡️")

st.title("🛡️ AI Use Policy")
st.caption("Green / yellow / red lanes - what AI may and may not touch.")

policy_path = Path(__file__).resolve().parents[2] / "governance" / "AI_Use_Policy.md"
if policy_path.exists():
    st.markdown(policy_path.read_text(encoding="utf-8"))
else:
    st.warning("Governance policy not found at governance/AI_Use_Policy.md")
