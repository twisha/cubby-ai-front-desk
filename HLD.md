# Cubby — High-Level Design

An AI front desk for early-learning centers, built around the health-report compliance
cycle. This document is the high-level view — system shape, the deterministic spine, and
the request flows a reviewer would want on one page before reading code. It sits between
`README.md` (product writeup + eval detail) and `DESIGN.md` (the full module-level spec) —
read this first, then drop into whichever of those two has the detail you need.

**Demo center:** Willow Grove Early Learning · Wissahocken, PA
**Stack:** FastAPI + Pydantic v2 · React (Vite) · Anthropic
**Status:** M0.0–M0.4b shipped

---

## Overview

Center admins spend hours a day answering the same handful of questions by phone, text,
and paper — and chasing one recurring compliance cycle that PA state law requires per
child. Cubby answers the everyday questions from the center's own handbook, and gives both
sides of the front desk — parent and staff — a shared, live view of the compliance loop: a
self-explaining reminder on one side, a scan-and-validate flow on the other.

This document covers system shape and decision flow, not the full module-by-module spec or
the product framing — those live in `DESIGN.md` and `README.md` respectively.

---

## Design thesis

> The model converts unstructured language ↔ structured data. **Every routing, validation,
> and scheduling decision is deterministic code** reading the model's structured output —
> never the reverse.

This is enforced structurally, not by convention: `core/llm/` returns Pydantic objects and
imports nothing from `core/rules/`; `core/rules/` is pure functions and imports no
Anthropic client at all. A reviewer can `grep -r anthropic backend/core/rules/` and get
nothing back — the boundary is a fact about the code, not a policy someone has to
remember.

---

## System context

```
                     ┌─────────────────────────────┐
   Parent  ───────▶  │                             │  ───────▶  Anthropic API
  (browser)          │   Cubby — FastAPI process   │            (chat · vision · judge)
                     │   single deployable          │
   Operator ───────▶ │   serves /api/* + built SPA │
  (browser,          │                             │
   same app,         └─────────────────────────────┘
   second tab)
```

One process, one URL, one origin — no separate vector DB, no worker service, no
cross-origin surface to secure. Parent and Operator are UI tabs in the same app, not
separate security boundaries (see [Security & cost controls](#security--cost-controls)).

---

## Architecture

```
                         ┌───────────────────────────────┐
                         │  core/llm/                     │
                         │  the ONLY Anthropic import      │
  routers/  ──────────▶  │  client.py   structured-output   │
  HTTP only —            │  answer.py   chat → AnswerResponse│
  parse request,         │  extract.py  vision → HealthForm  │
  call core,             │  judge.py    groundedness/faithful │
  shape response          └───────────────┬───────────────┘
                                           │  Pydantic out
                                           ▼
                         ┌───────────────────────────────┐
                         │  core/rules/                   │
                         │  ZERO Anthropic imports          │
                         │  routing.py     → AnswerMode      │
                         │  validation.py  → accept/reject    │
                         │  scheduler.py   → tier              │
                         └───────────────────────────────┘

                         core/retrieval/ · core/store/
                         Retriever & Store interfaces — the two upgrade seams
```

Data only ever flows one direction, LLM zone → rules zone, never back. `routers/` is the
only layer allowed to see both zones at once.

---

## The deterministic spine

Four places a reviewer should read first — each takes model output and makes the call.

### 1. Answer routing — `core/rules/routing.py`
Sensitive-topic and courtesy checks run on the raw question, before retrieval or the model.
After the model runs, `route()` maps its structured fields to a mode — first match wins.
**Modes:** `grounded` · `judgment` · `escalated` · `gap`

### 2. Form validation — `core/rules/validation.py`
The model reports what it *sees* on a photographed form — signature present, exam date,
credential. Code enforces the trap: parent-signed but examiner-unsigned is a hard reject,
never a pass. **Verdicts:** `accepted` · `rejected` · `needs_review`

### 3. Compliance scheduler — `core/rules/scheduler.py`
Pure date math, no model in the loop at all: cycle length from age band (55 Pa. Code
§3270.131(b)), tier from days-to-due, pause/grace state from the acknowledged appointment
date. **Tiers:** `compliant → gentle → standard → urgent → overdue`

### 4. Gap → policy flywheel — `core/llm/draft.py` + operator approve
The model may *draft* a new handbook section from a cluster of unanswered questions.
Publishing it — re-chunk, re-embed, go live — is a human clicking approve, a real
human-in-the-loop (HITL) gate, not a code gate. **Flow:** `draft (LLM) → approve (human) →
re-index (code)`

---

## Request flows

### POST /api/ask — parent question → answer

```
question ──▶ courtesy/sensitive     ──▶ retrieval +        ──▶ answer engine   ──▶ route()   ──▶ trace + log
             pre-check (code)           gap gate (code)        (Haiku, LLM)        (code)         (LangSmith
             before retrieval           score<0.30 skips LLM                                       tag by mode)
```

Every branch — including the two gates that skip the LLM entirely — is traced and tagged
by mode, so an escalated or gap question is visible in observability whether or not a model
call happened underneath.

### POST /api/validate-form — staff scans a health form

```
photo ──▶ vision extract     ──▶ fuzzy-match      ──▶ validate()        ──▶ accepted →
          (Sonnet, LLM)           child (code)          signature/credential/  roster update
                                                          date/attestation
```

Rejected or unmatched scans surface in the operator's *Needs attention* queue with the
exact failing check and a one-tap parent-notify action — nothing silently disappears.

### POST /api/acknowledge — the money-shot loop

```
parent taps "We have an   ──▶  scheduler state transition   ──▶  operator dashboard
appointment" + date picker      pure date math, no LLM             reflects live on next refetch
```

appt ≤ due → reminders pause. appt > due → an explicit, timestamped "grace requested" chip
instead of a silent pause — the one case that's a real judgment call, made visible rather
than automated away.

---

## Data model

M0 shape — in-memory now, same fields once `Store` swaps to SQLite.

| Entity | Fields | Purpose |
|---|---|---|
| `Child` | id, name, dob, last_exam_date, parent_state, acknowledged_appt_date | The roster row the scheduler reads and the validator writes back to on accept |
| `QuestionLog` | id, ts, text, mode, max_cosine, source_ids, answer, judge_flag | Every question ever asked, with the signals the "struggled" view needs |
| `HealthFormExtraction` / `ValidationResult` | model-seen fields → verdict + issues | What the model saw on a form, and the deterministic verdict + parent-friendly `ValidationIssue` list computed from it |
| `GapGroup` | theme, count, questions[] | GAP-mode questions clustered by shared keyword, the read-only precursor to the live draft→approve flywheel |

---

## Two upgrade seams

| Seam | Interface | Today | Next | Rule |
|---|---|---|---|---|
| `Retriever` | `search(query) -> (entries, max_score)` | keyword overlap | embeddings + FAISS | routing code never changes — it only ever sees the interface |
| `Store` | typed CRUD over questions, roster, gaps | in-memory dicts | SQLite | routers never change — same rule, different seam |

Rule of thumb applied throughout: **if upgrading a seam ever touches a router or a decision
module, the seam was drawn in the wrong place.**

---

## Security & cost controls

Threat model, ranked — cheapest control last, hard cap always wins.

| Priority | Risk | Control |
|---|---|---|
| 1 | Cost abuse of a public LLM-backed endpoint | Global daily call cap, fails closed (429) — the real backstop |
| 2 | API key / credit theft | Key server-only, never logged, never shipped to client |
| 3 | Unauthorized access | Shared access code + email capture, enforced server-side on every `/api/*` route |

Explicitly not defended, by stated design: RBAC, per-user auth, multi-tenant isolation.
Parent/Operator tabs are UI views in one app, not security boundaries — a deliberate scope
line for a reviewer demo, not an oversight.

---

## Observability

Every `/api/ask` request runs inside a single LangSmith span, tagged with the resulting
mode and a `sensitive` flag — including the branches that never reach the model at all
(courtesy, the sensitive pre-check, the sub-threshold gap gate). A model call, when one
happens, appears as a nested child span. This closes a real gap found while dogfooding: an
escalation-worthy question that skipped the LLM used to produce *no trace at all*, which
made "why didn't the model catch this" the wrong question to even ask.

---

## Evals

27-case golden set, run against the real production pipeline. Generator (Haiku) ≠ judge
(Sonnet).

| Metric | Result |
|---|---|
| Recall@4 | 0.80 |
| MRR | 0.74 |
| Gap-gate precision | 83% (20/24) |
| Mode-routing correctness | 88% (23/26) |
| Groundedness | 94% (16/17) |
| Faithfulness | 100% (17/17) |
| Accuracy vs. reference | 100% (17/17) |
| Judge calibration (trap case) | 100% (1/1) |

**23/27 passed overall** — every failure has a documented root cause (keyword-retrieval
misses without stemming, one reproducible hallucination on an unstated allergy inference,
one judge bug found and fixed) rather than being hand-waved. Full breakdown in
`evals/results.md`.

---

## Deployment

```
Dockerfile ──▶ FastAPI process ──▶ Render
(builds        (serves /api/*      (render.yaml)
frontend,       + static SPA)
pre-downloads
model weights)
```

One image, one process, one URL.

---

## Roadmap

M0 is the submission boundary. Everything after swaps one stub at a time.

1. **M0.0–M0.4b (shipped)** — scaffold, grounded chat, vision validation, compliance
   dashboard + acknowledge, access gate + cost breakers, gaps panel, Dockerfile/Render
   deploy.
2. **M1** — `FaissRetriever` behind the existing `Retriever` seam.
3. **M2** — `SqliteStore` behind the existing `Store` seam.
4. **M3** — live gap draft → approve → re-index flywheel (today's panel is read-only).
5. **M4/M5** — eval harness already shipped ahead of schedule; sampled runtime judging
   next.
