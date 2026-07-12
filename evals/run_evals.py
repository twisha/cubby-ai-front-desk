"""Offline eval harness (SPEC Quality & Evals).

Runs the golden set against the REAL production pipeline -- backend.routers.
ask.ask() called directly as a plain function, not through HTTP. Depends()
markers only matter to FastAPI's routing machinery; calling the function
directly with explicit retriever/store arguments skips the rate limiter and
auth gate entirely while running the exact same decision code that's
deployed. Zero drift between what's tested and what's shipped.

Metrics:
- Relevance: Recall@4, MRR from the retriever's own rankings; gap-gate
  precision (in-scope clears the 0.30 threshold, out-of-scope falls below).
- Groundedness: Sonnet judge sees ONLY the cited sections + the answer.
- Faithfulness: judge checks qualifiers/thresholds/exceptions are preserved.
- Accuracy: judge scores the actual answer against a reference answer.
- Mode-routing correctness: actual mode vs. expected mode.
- Judge calibration: a hardcoded bad answer (real system never produces it)
  proves the faithfulness judge itself catches an omitted qualifier.

Generator (Haiku, via the live /ask pipeline) != judge (Sonnet, judge.py) --
never the same model grading itself.

Run: python evals/run_evals.py   (needs ANTHROPIC_API_KEY in the environment)
Prints a markdown table and writes evals/results.md.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.core.llm.judge import judge_accuracy, judge_faithfulness, judge_groundedness
from backend.core.retrieval.chunker import chunk_handbook
from backend.core.retrieval.index import KeywordRetriever
from backend.core.store.repo import InMemoryStore
from backend.routers.ask import AskRequest, ask

GOLDEN_PATH = Path(__file__).parent / "golden_set.jsonl"
RESULTS_PATH = Path(__file__).parent / "results.md"


def load_cases() -> list[dict]:
    with GOLDEN_PATH.open() as f:
        return [json.loads(line) for line in f if line.strip()]


@dataclass
class CaseResult:
    id: str
    category: str
    expected_mode: str | None = None
    ok: bool = True
    notes: list[str] = field(default_factory=list)
    recall_at_4: float | None = None
    reciprocal_rank: float | None = None
    gap_gate_correct: bool | None = None
    actual_mode: str | None = None
    mode_correct: bool | None = None
    groundedness: str | None = None
    faithfulness: str | None = None
    accuracy: str | None = None


def eval_retrieval(case: dict, retriever: KeywordRetriever) -> tuple[float | None, float | None, bool | None]:
    """Recall@4, reciprocal rank, gap-gate correctness — retriever only, no LLM."""
    expected_ids = set(case.get("expected_section_ids") or [])
    ordered, max_score = retriever.search(case["question"])
    top4_ids = {e.id for e in ordered[:4]}

    recall4 = rr = None
    if expected_ids:
        recall4 = 1.0 if expected_ids & top4_ids else 0.0
        rr = 0.0
        for rank, e in enumerate(ordered, start=1):
            if e.id in expected_ids:
                rr = 1.0 / rank
                break

    gap_gate_correct = None
    if case["expected_mode"] == "gap":
        gap_gate_correct = max_score < retriever.gap_threshold
    elif case["expected_mode"] in ("grounded", "judgment"):
        gap_gate_correct = max_score >= retriever.gap_threshold
    # escalated cases bypass retrieval via detect_sensitive() -- gap-gate
    # precision isn't a meaningful measurement for them.

    return recall4, rr, gap_gate_correct


def run_live_case(case: dict, retriever: KeywordRetriever, store: InMemoryStore) -> CaseResult:
    r = CaseResult(id=case["id"], category=case["category"], expected_mode=case["expected_mode"])
    r.recall_at_4, r.reciprocal_rank, r.gap_gate_correct = eval_retrieval(case, retriever)

    resp = ask(AskRequest(question=case["question"]), retriever=retriever, store=store)
    r.actual_mode = resp.mode.value
    r.mode_correct = r.actual_mode == case["expected_mode"]
    if not r.mode_correct:
        r.ok = False
        r.notes.append(f"expected mode {case['expected_mode']}, got {r.actual_mode}")

    # Groundedness/faithfulness/accuracy only apply where a real LLM answer
    # was produced. Gap/escalated answers are fixed templates -- nothing to
    # judge (and "zero fabrication" is trivially true for a hardcoded string).
    if case["expected_mode"] in ("grounded", "judgment") and resp.sources:
        cited_text = "\n\n".join(f"[{s.id}] {s.content}" for s in resp.sources)

        gv = judge_groundedness(cited_text, resp.answer)
        r.groundedness = gv.verdict
        if gv.verdict != "yes":
            r.ok = False
            r.notes.append(f"groundedness={gv.verdict}: {gv.failing_claim}")

        fv = judge_faithfulness(case["question"], cited_text, resp.answer)
        r.faithfulness = fv.verdict
        if fv.verdict != "pass":
            r.ok = False
            r.notes.append(f"faithfulness=fail: {fv.reason}")

        if case.get("expected_answer"):
            av = judge_accuracy(case["question"], case["expected_answer"], resp.answer)
            r.accuracy = av.verdict
            if av.verdict != "pass":
                r.ok = False
                r.notes.append(f"accuracy=fail: {av.reason}")

    return r


def run_judge_calibration_case(case: dict, handbook_by_id: dict) -> CaseResult:
    """No live system call -- feeds a HARDCODED bad answer straight to the
    faithfulness judge, proving the judge itself catches an omitted
    qualifier. This is the SPEC's mandatory calibration case: an illness
    answer omitting "without fever-reducing medication" must FAIL
    faithfulness even though it would be grounded."""
    r = CaseResult(id=case["id"], category=case["category"])
    source = handbook_by_id[case["source_id"]]
    fv = judge_faithfulness(case["question"], source.content, case["hardcoded_answer"])
    r.faithfulness = fv.verdict
    r.ok = fv.verdict == case["expected_judge_verdict"]
    if not r.ok:
        r.notes.append(
            f"expected judge verdict {case['expected_judge_verdict']}, got {fv.verdict}: {fv.reason}"
        )
    return r


def pct(n: int, d: int) -> str:
    return f"{100 * n / d:.0f}%" if d else "n/a"


def render_report(results: list[CaseResult]) -> str:
    live = [r for r in results if r.actual_mode is not None]
    retrieval_cases = [r for r in results if r.recall_at_4 is not None]
    gap_gate_cases = [r for r in results if r.gap_gate_correct is not None]
    graded = [r for r in results if r.groundedness is not None]
    accuracy_cases = [r for r in graded if r.accuracy is not None]
    calibration = [r for r in results if r.id.startswith("jc")]

    recall_avg = sum(r.recall_at_4 for r in retrieval_cases) / len(retrieval_cases) if retrieval_cases else None
    mrr_avg = sum(r.reciprocal_rank for r in retrieval_cases) / len(retrieval_cases) if retrieval_cases else None
    gap_gate_ok = sum(1 for r in gap_gate_cases if r.gap_gate_correct)
    mode_ok = sum(1 for r in live if r.mode_correct)
    grounded_ok = sum(1 for r in graded if r.groundedness == "yes")
    faithful_ok = sum(1 for r in graded if r.faithfulness == "pass")
    accuracy_ok = sum(1 for r in accuracy_cases if r.accuracy == "pass")
    calib_ok = sum(1 for r in calibration if r.ok)
    overall_ok = sum(1 for r in results if r.ok)

    lines: list[str] = []
    lines.append("# Cubby Eval Results\n")
    lines.append(f"**{overall_ok}/{len(results)} cases passed.**\n")
    lines.append("## Summary\n")
    lines.append("| Metric | Result |")
    lines.append("|---|---|")
    lines.append(f"| Recall@4 (retrieval readiness) | {recall_avg:.2f} ({len(retrieval_cases)} cases) |")
    lines.append(f"| MRR | {mrr_avg:.2f} |")
    lines.append(f"| Gap-gate precision | {pct(gap_gate_ok, len(gap_gate_cases))} ({gap_gate_ok}/{len(gap_gate_cases)}) |")
    lines.append(f"| Mode-routing correctness | {pct(mode_ok, len(live))} ({mode_ok}/{len(live)}) |")
    lines.append(f"| Groundedness (verdict=yes) | {pct(grounded_ok, len(graded))} ({grounded_ok}/{len(graded)}) |")
    lines.append(f"| Faithfulness (verdict=pass) | {pct(faithful_ok, len(graded))} ({faithful_ok}/{len(graded)}) |")
    lines.append(f"| Accuracy vs. reference | {pct(accuracy_ok, len(accuracy_cases))} ({accuracy_ok}/{len(accuracy_cases)}) |")
    lines.append(f"| Judge calibration (mandatory trap) | {pct(calib_ok, len(calibration))} ({calib_ok}/{len(calibration)}) |")
    lines.append("")

    lines.append("## Per-case detail\n")
    lines.append("| id | category | mode (exp -> actual) | recall@4 | grounded | faithful | accuracy | notes |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for r in results:
        mode_cell = "-" if r.actual_mode is None else f"{r.expected_mode} -> {r.actual_mode}" + ("" if r.mode_correct else " ⚠")
        recall_cell = "-" if r.recall_at_4 is None else f"{r.recall_at_4:.0f}"
        note = "; ".join(r.notes)[:120]
        status = "✅" if r.ok else "❌"
        lines.append(
            f"| {r.id} | {r.category} | {mode_cell} | {recall_cell} | "
            f"{r.groundedness or '-'} | {r.faithfulness or '-'} | {r.accuracy or '-'} | "
            f"{status} {note} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    entries = chunk_handbook()
    handbook_by_id = {e.id: e for e in entries}
    retriever = KeywordRetriever(entries)
    store = InMemoryStore()

    cases = load_cases()
    results: list[CaseResult] = []
    for case in cases:
        print(f"  running {case['id']}...", file=sys.stderr)
        if case["type"] == "judge_calibration":
            results.append(run_judge_calibration_case(case, handbook_by_id))
        else:
            results.append(run_live_case(case, retriever, store))

    report = render_report(results)
    print(report)
    RESULTS_PATH.write_text(report)
    print(f"\n(written to {RESULTS_PATH})", file=sys.stderr)

    if any(not r.ok for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
