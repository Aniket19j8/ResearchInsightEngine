"""Document Analysis - upload a document or fetch a research paper, then
get an AI summary, key points, and any techniques mentioned.

PII is scrubbed before any text reaches the LLM (handled in synthesis).
"""
import json
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from src import config, repository, synthesis

st.set_page_config(page_title="Document Analysis", page_icon="📄", layout="wide")
repository.init_db()

st.title("📄 Document Analysis & Literature Review")
st.caption("Summarize uploaded documents or search research papers for new techniques.")

with st.expander("ℹ️ How to use this page"):
    st.markdown(
        "**Two ways to use this page:**\n\n"
        "1. **Summarize a document** - upload a `.txt`, `.md`, or `.pdf`, or paste "
        "text, then click **Summarize**. You get a short summary, key points, and "
        "any research techniques mentioned.\n"
        "2. **Search papers** - type a topic and pick a source (**arXiv** for "
        "STEM/ML preprints, **Semantic Scholar** for all fields), then summarize an "
        "abstract that looks relevant.\n\n"
        "*Example document:* a usability report, a research paper, or meeting notes.\n"
        "*Example paper search:* `thematic analysis qualitative UX research`"
    )


def _extract_text(uploaded) -> str:
    """Read text from an uploaded txt/md/pdf file."""
    name = uploaded.name.lower()
    if name.endswith(".pdf"):
        try:
            from pypdf import PdfReader

            reader = PdfReader(uploaded)
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as e:
            st.error(f"Could not read PDF: {e}")
            return ""
    return uploaded.read().decode("utf-8", errors="ignore")


def _search_arxiv(query: str) -> list[dict]:
    """Return up to 5 arXiv papers as {title, abstract, link}."""
    url = (
        "https://export.arxiv.org/api/query?search_query=all:"
        + urllib.parse.quote(query)
        + "&start=0&max_results=5"
    )
    with urllib.request.urlopen(url, timeout=15) as resp:
        xml_data = resp.read()
    ns = {"a": "http://www.w3.org/2005/Atom"}
    papers = []
    for entry in ET.fromstring(xml_data).findall("a:entry", ns):
        papers.append({
            "title": entry.findtext("a:title", default="(no title)", namespaces=ns).strip(),
            "abstract": entry.findtext("a:summary", default="", namespaces=ns).strip(),
            "link": entry.findtext("a:id", default="", namespaces=ns).strip(),
            "tldr": "",
        })
    return papers


def _search_semantic_scholar(query: str) -> list[dict]:
    """Return up to 5 Semantic Scholar papers as {title, abstract, link, tldr}."""
    fields = "title,abstract,url,tldr"
    url = (
        "https://api.semanticscholar.org/graph/v1/paper/search?query="
        + urllib.parse.quote(query)
        + f"&limit=5&fields={fields}"
    )
    req = urllib.request.Request(url)
    if config.SEMANTIC_SCHOLAR_API_KEY:
        req.add_header("x-api-key", config.SEMANTIC_SCHOLAR_API_KEY)
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
    papers = []
    for p in data.get("data", []):
        tldr = (p.get("tldr") or {}).get("text") or ""
        papers.append({
            "title": p.get("title") or "(no title)",
            "abstract": p.get("abstract") or "",
            "link": p.get("url") or "",
            "tldr": tldr,
        })
    return papers


def _render_summary(result: dict) -> None:
    if result.get("pii_report"):
        from src import privacy

        st.warning("🔒 " + privacy.summarize_report(result["pii_report"]))
    st.caption(f"Generated via **{result.get('source', '?')}**")
    st.subheader("Summary")
    st.write(result.get("summary", ""))
    key_points = result.get("key_points", [])
    if key_points:
        st.subheader("Key points")
        for p in key_points:
            st.markdown(f"- {p}")
    techniques = result.get("techniques", [])
    if techniques:
        st.subheader("Techniques mentioned")
        for t in techniques:
            st.markdown(f"- {t}")


# --- Section 1: Summarize a document ---------------------------------------
st.header("1. Summarize a document")

tab_upload, tab_paste = st.tabs(["Upload a file", "Paste text"])

with tab_upload:
    uploaded = st.file_uploader(
        "Upload a document", type=["txt", "md", "pdf"],
        help="Supported: .txt, .md, .pdf",
    )
    if uploaded and st.button("Summarize file", type="primary"):
        text = _extract_text(uploaded)
        if text.strip():
            with st.spinner("Summarizing..."):
                _render_summary(synthesis.summarize_document(text))
        else:
            st.warning("No text could be extracted from that file.")

with tab_paste:
    pasted = st.text_area(
        "Paste document text", height=220,
        placeholder="Paste a report, paper, or notes here...",
    )
    if pasted.strip() and st.button("Summarize text", type="primary"):
        with st.spinner("Summarizing..."):
            _render_summary(synthesis.summarize_document(pasted))

# --- Section 2: Search research papers -------------------------------------
st.divider()
st.header("2. Search research papers")

col_q, col_src = st.columns([3, 1])
paper_query = col_q.text_input(
    "Search query", placeholder="thematic analysis qualitative UX research",
    help="Searches paper titles/abstracts. Needs internet access.",
)
source = col_src.selectbox(
    "Source", ["arXiv", "Semantic Scholar"],
    help="arXiv: STEM/ML preprints. Semantic Scholar: all fields, broader coverage.",
)

if source == "Semantic Scholar" and not config.SEMANTIC_SCHOLAR_API_KEY:
    st.caption("Using Semantic Scholar without an API key (lower shared rate limit). "
               "Add SEMANTIC_SCHOLAR_API_KEY to .env for a faster, dedicated limit.")

if st.button("Search papers") and paper_query.strip():
    try:
        with st.spinner(f"Searching {source}..."):
            if source == "arXiv":
                papers = _search_arxiv(paper_query.strip())
            else:
                papers = _search_semantic_scholar(paper_query.strip())
        st.session_state["papers"] = papers
        st.session_state["papers_source"] = source
    except Exception as e:
        st.error(f"{source} search failed (check your internet connection / rate limit): {e}")

papers = st.session_state.get("papers", [])
if papers:
    st.caption(f"{len(papers)} result(s) from **{st.session_state.get('papers_source', '')}**.")
    for idx, paper in enumerate(papers):
        with st.container(border=True):
            st.markdown(f"**{paper['title']}**")
            if paper.get("link"):
                st.caption(paper["link"])
            if paper.get("tldr"):
                st.info(f"TL;DR: {paper['tldr']}")
            abstract = paper.get("abstract") or "(No abstract available.)"
            st.write(abstract[:600] + ("..." if len(abstract) > 600 else ""))
            if abstract and abstract != "(No abstract available.)":
                if st.button("Summarize this abstract", key=f"sum_{idx}"):
                    with st.spinner("Summarizing..."):
                        _render_summary(synthesis.summarize_document(abstract))
