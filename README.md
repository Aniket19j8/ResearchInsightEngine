# UX Research Insight Engine

**Deployed Link: https://researchinsightengine-u3pwqlztrjebvqordi5hhn.streamlit.app/**

> AI accelerates the busywork; the researcher always owns the interpretation.

A small system that takes a raw interview transcript, uses AI to do a *first pass*
at tagging themes and drafting insights, then makes a human researcher review and
approve everything before it's saved. Approved insights go into a searchable
repository with a controlled taxonomy, and a dashboard tracks time saved and reuse.

> Portfolio project for the EdPlus role: **UX Researcher, Systems & AI Enablement**.
> See `BUILD_GUIDE.md` for the full rationale and interview talking points.

## Workflow

`Intake → AI Synthesis → Human Review gate → Repository → Retrieval → Dashboard`

## Run locally

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1        # Windows PowerShell
pip install -r requirements.txt

copy .env.example .env            # then add your OPENAI_API_KEY
streamlit run app/Home.py
```

Without an API key the app runs in **keyword-fallback mode**, so the full
workflow still works for testing.

## Features

- **Intake → Synthesis → Human Review → Repository → Search** core workflow
- **PII auto-redaction** before any text reaches the LLM (`src/privacy.py`)
- **Document analysis**: upload `.txt`/`.md`/`.pdf` or search arXiv papers, then summarize
- **Study reports**: one-click executive summary with downloadable Markdown
- **Ops dashboard**: time-to-insight, AI override rate, reuse, CSV export
- **Per-page usage hints** with examples ("ℹ️ How to use this page")

## Project layout

```
data/        taxonomy, transcripts, SQLite + Chroma stores
src/         config, llm, synthesis, privacy, repository, retrieval, metrics
app/         Streamlit Home + workflow pages (Intake, Synthesis, Search,
             Dashboard, Governance, Document Analysis, Study Report)
governance/  AI_Use_Policy.md (green/yellow/red lanes)
docs/        demo script, usability test notes, DEPLOY.md
outputs/     metrics_export.csv (feeds Tableau)
Dockerfile   production image (Python 3.12)
```

## Deploy

See [`docs/DEPLOY.md`](docs/DEPLOY.md) for Docker, Hugging Face Spaces,
Streamlit Cloud, and AWS (App Runner / ECS / EC2) instructions.
