# Cubby — AI Front Desk

An AI front desk for **Willow Grove Early Learning** (Wissahocken, PA), focused on
the PA health-report compliance loop — the one broken loop both parents and staff
see from opposite sides.

**Design thesis:** the LLM converts unstructured language ↔ structured data
(answering from the handbook, extracting fields from a photographed CD-51 form).
**Every routing, validation, and scheduling decision is deterministic code** reading
the model's structured output. The model never decides what UI to render or whether
a form is compliant — code does.

This is enforced structurally: `backend/core/llm/` returns Pydantic and imports no
decision code; `backend/core/rules/` (routing, validation, scheduler) is pure
functions and imports no Anthropic client.

## Stack
- **Backend:** FastAPI + Pydantic v2 (Python 3.11+)
- **Frontend:** React (Vite) + Tailwind, mobile-first, two tabs — built and served by
  FastAPI as static files (single deployable, one URL)
- **LLM:** Anthropic — `claude-haiku-4-5` (chat + gap draft), `claude-sonnet-5`
  (CD-51 vision extraction + judge). Key from `ANTHROPIC_API_KEY`.
- **Retrieval:** keyword gate in M0; Chroma + `all-MiniLM-L6-v2` behind the
  `Retriever` seam in M1.

## Run (M0.0)
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # fill ANTHROPIC_API_KEY when chat/vision land (M0.1+)
uvicorn backend.main:app --reload
# open http://127.0.0.1:8000  ·  GET /api/health
```

## Milestones
Built as modular, individually committed increments — the app boots and demos at
every commit. **M0.0** scaffold · **M0.1** grounded chat · **M0.2** CD-51 vision
validation · **M0.3** compliance dashboard + acknowledge · **M0.4** gaps panel +
access gate + deploy. Post-submission: M1 Chroma retrieval · M2 SQLite · M3 live
gap flywheel · M4 eval harness.
