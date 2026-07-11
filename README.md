# Cubby — AI Front Desk

Cubby is an AI front desk for early-learning centers. It answers parents' everyday
questions from the center's own handbook and runs the loop that centers handle worst:
the recurring, per-child **health-report compliance cycle** that state law requires —
seen from both sides of the front desk at once.

Each center is a tenant: its own handbook, roster, policies, and jurisdiction rules.
This repository ships with one fully seeded reference center — **Willow Grove Early
Learning** (a fictional center in Wissahocken, PA) — so the whole experience is
demoable end to end, but nothing about the center is hard-coded. Swap the handbook and
roster and the same app serves a different center.

**Design thesis:** the LLM converts unstructured language ↔ structured data
(answering from the handbook, extracting fields from a photographed health form).
**Every routing, validation, and scheduling decision is deterministic code** reading
the model's structured output. The model never decides what UI to render or whether a
form is compliant — code does.

This is enforced structurally: `backend/core/llm/` returns Pydantic and imports no
decision code; `backend/core/rules/` (routing, validation, scheduler) is pure functions
and imports no Anthropic client. A reviewer can grep to verify the boundary holds.

## What it does

**Parent side** — a grounded Q&A chat (answers cite the handbook; uncertain or
sensitive questions hand off gracefully to a human) plus a self-explaining health-report
reminder card with one-tap "we have an appointment" acknowledgment.

**Operator side** — scan a paper health form and get instant accept/reject-with-fix at
the desk; a compliance dashboard of every child's cycle state sorted by urgency; and a
questions-and-gaps log where the questions Cubby couldn't answer become new handbook
sections (the draft → approve flywheel).

## Stack

- **Backend:** FastAPI + Pydantic v2 (Python 3.11+)
- **Frontend:** React (Vite) + Tailwind, mobile-first, two tabs — built and served by
  FastAPI as static files (single deployable, one URL)
- **LLM:** Anthropic — `claude-haiku-4-5` (chat + gap draft), `claude-sonnet-5`
  (health-form vision extraction + judge). Key from `ANTHROPIC_API_KEY`.
- **Retrieval:** keyword gate in M0; Chroma + `all-MiniLM-L6-v2` behind the `Retriever`
  seam in M1.

## Run

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # fill ANTHROPIC_API_KEY when chat/vision land (M0.1+)
uvicorn backend.main:app --reload
# open http://127.0.0.1:8000  ·  GET /api/health
```

## Scaling to many centers

The demo grounds on one authored `handbook.md`; production centers don't have markdown.
The architecture is built so the path to many tenants is a set of swaps behind existing
seams, not a rewrite:

1. **Ingest real documents.** A center uploads its Word/PDF/Google-Doc handbook; a
   pipeline emits the same `HandbookEntry` sections the app already indexes. Provenance
   is preserved for citations, and an operator review step (the same UI as gap-approve)
   gates anything before it goes live — trustworthy without perfect parsing.
2. **Don't RAG what's already a record.** Tuition, hours, closures, roster, DOB, and
   health-form due dates live in a center's management system. Answer those by querying
   the system of record (always fresh, never hallucinated); reserve retrieval for
   narrative policy prose.
3. **Multi-tenant + multi-state.** One retrieval collection and one config per center;
   the deterministic scheduler stays put and only its §3270.131-style rules table is
   swapped per jurisdiction.

At one small handbook, full-context grounding is enough; at N centers × multi-page docs
it isn't — which is why real retrieval lives behind the `Retriever` seam from day one.

## How it's built

Modular, individually committed increments — the app boots and demos at every commit.
Two seams make later work one-file swaps: `Retriever` (keyword → Chroma) and `Store`
(in-memory → SQLite), so a retrieval or persistence upgrade never touches a router or a
decision module.

**M0.0** scaffold · **M0.1** grounded chat · **M0.2** health-form vision validation ·
**M0.3** compliance dashboard + acknowledge · **M0.4** gaps panel + access gate + deploy.
Post-submission: M1 Chroma retrieval · M2 SQLite · M3 live gap flywheel · M4 eval harness.
