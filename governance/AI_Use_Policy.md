# AI Use Policy — UX Research Insight Engine

A one-page policy defining where AI may operate, where it must be verified,
and where it is never allowed. The lanes let the team move fast *safely*.

## 🟢 Green lane — AI allowed
- First-pass tagging of transcripts against the controlled taxonomy.
- Drafting candidate insight wording.
- Summarization of long transcripts.

## 🟡 Yellow lane — AI + mandatory human verification
- Theme assignment.
- Severity rating.
- Anything surfaced in retrieval that informs a decision.

## 🔴 Red lane — no AI
- Final interpretation and publishing of an insight.
- Any text containing participant PII before it is pseudonymized.
- Live session moderation.

## PII handling
- Stripping names, emails, and identifiers before sending text
  to any external model.

## Prompt versioning & auditability
- Prompts are version-controlled.
- The audit log records, for every suggestion, the AI's original value and
  the human's final decision (approve / edit / reject) with a timestamp.
