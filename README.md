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
cp .env.example .env            # fill in ANTHROPIC_API_KEY
```

The backend serves `/api/*` and the built frontend from one process, but the
frontend has to actually be built first — `frontend/dist` is gitignored, so a
fresh clone doesn't have it. Pick one of the two setups below.

**A. Iterating on the frontend (recommended for development)** — two
terminals, hot reload on every source change, nothing to rebuild by hand:

```bash
# terminal 1
uvicorn backend.main:app --reload --env-file .env
# terminal 2
cd frontend && npm install && npm run dev
# open http://localhost:5173  ·  Vite proxies /api/* to :8000
```

**B. Single process, closer to how it deploys** — build once, then the
backend alone serves everything on one port:

```bash
cd frontend && npm install && npm run build && cd ..
uvicorn backend.main:app --reload --env-file .env
# open http://127.0.0.1:8000  ·  GET /api/health
```

With setup B, **any frontend change requires `npm run build` again** before
it shows up — `--reload` restarts the backend on Python changes, but it
doesn't know to rebuild the frontend. If you edit frontend code and the UI
looks unchanged, that stale build is almost always why: rebuild and
hard-refresh the browser tab.

**C. Docker** — matches the Render deploy (`Dockerfile` builds the frontend
and serves it from one image):

```bash
docker build -t cubby . && docker run -p 8000:8000 --env-file .env cubby
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

## Quality & evals

Generator (Haiku, the live answer engine) != judge (Sonnet, `core/llm/judge.py`) — never
the same model grading itself. `evals/golden_set.jsonl` (27 cases) runs against the real
production pipeline — `backend.routers.ask.ask()` called directly as a plain function, not
through HTTP, so results have zero drift from what's deployed and the rate limiter/auth
gate never enter the picture.

Run `python evals/run_evals.py` (needs `ANTHROPIC_API_KEY`). Prints this table and writes
`evals/results.md`.

| Metric | Result |
|---|---|
| Recall@4 (retrieval readiness) | 0.80 |
| MRR | 0.74 |
| Gap-gate precision | 83% (20/24) |
| Mode-routing correctness | 88% (23/26) |
| Groundedness | 94% (16/17) |
| Faithfulness | 100% (17/17) |
| Accuracy vs. reference | 100% (17/17) |
| Judge calibration (mandatory trap) | 100% (1/1) |

**23/27 passed — every failure is explained, not hand-waved:**

- **3 retrieval misses** (late-pickup, "threw up," "rash") — the M0 `KeywordRetriever` does
  exact-token matching with no stemming, so "picking up" never matches "pickup." This is
  exactly the question Recall@4/MRR exist to answer: retrieval alone **isn't yet safe to
  trust**, which is why real embeddings (M1) sit behind the `Retriever` seam instead of
  touching decision code. One near-miss ("bring my dog to pickup," score 0.333, above
  threshold) shows the defense-in-depth working anyway: the gate let it through, but the
  model's own empty `source_ids` still routed it to GAP.
- **1 reproducible groundedness miss** — asked about an allergy plan, Haiku consistently
  (4/4 runs) adds "if your child has no allergies, none is needed" — correct and helpful,
  but an *unstated* inverse of the handbook's literal rule. A prompt fix naming this exact
  case verbatim didn't change the behavior. That's the honest finding: not a bug to patch
  away, but why groundedness needs to be an ongoing automated check, not a one-time prompt
  fix — the same habit could silently assert something false against a less symmetric rule.
- **The mandatory faithfulness-calibration case passes** — a hardcoded answer omitting
  "without fever-reducing medication" is correctly flagged `fail`, proving the judge has
  real discriminating power.
- **A real judge bug was found and fixed here**: the faithfulness judge originally didn't
  receive the question, so it flagged any answer that didn't restate the entire source
  section — failing "we close at 6pm" for not repeating the opening time. Passing the
  question through fixed it.

## How it's built

Modular, individually committed increments — the app boots and demos at every commit.
Two seams make later work one-file swaps: `Retriever` (keyword → Chroma) and `Store`
(in-memory → SQLite), so a retrieval or persistence upgrade never touches a router or a
decision module.

**Done:** M0.0 scaffold · M0.1 grounded chat · M0.2 health-form vision validation · M0.3
compliance dashboard + acknowledge · M0.4a access gate + cost circuit-breakers · eval
harness (moved up — the assignment scores on it directly) · dark/light theme · LangSmith
tracing. **Next:** gaps panel + deploy. **Post-submission:** Chroma retrieval, SQLite, live
gap flywheel.
