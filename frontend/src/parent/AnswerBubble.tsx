import type { AskResponse } from "../api";
import CitationChip from "./CitationChip";

/**
 * Renders purely on `response.mode` — the backend already decided the mode
 * (core/rules/routing.py); this component never re-derives it, only displays
 * what code already chose.
 */
export default function AnswerBubble({ response }: { response: AskResponse }) {
  switch (response.mode) {
    case "grounded":
      return (
        <div className="rounded-2xl bg-white p-3.5 shadow-sm">
          <p className="m-0 text-[15px] leading-snug">{response.answer}</p>
          {response.sources.length > 0 && (
            <div className="mt-2.5">
              {response.sources.map((s) => (
                <CitationChip key={s.id} source={s} />
              ))}
            </div>
          )}
        </div>
      );

    case "judgment":
      return (
        <div className="rounded-2xl bg-white p-3.5 shadow-sm">
          <p className="m-0 text-[15px] leading-snug">{response.answer}</p>
          {response.sources.length > 0 && (
            <div className="mt-2.5">
              {response.sources.map((s) => (
                <CitationChip key={s.id} source={s} />
              ))}
            </div>
          )}
          <div
            className="mt-2.5 rounded-lg px-3 py-2 text-xs font-semibold"
            style={{ backgroundColor: "var(--cubby-amber-bg)", color: "var(--cubby-amber)" }}
          >
            ⚠ Flagged for Ms. Rivera — typical reply &lt; 15 min
          </div>
        </div>
      );

    case "escalated":
    case "gap":
      return (
        <div
          className="rounded-2xl p-3.5 border"
          style={{ backgroundColor: "#fff5f3", borderColor: "var(--cubby-coral)" }}
        >
          <p className="m-0 text-[15px] leading-snug" style={{ color: "var(--cubby-ink)" }}>
            💌 {response.answer}
          </p>
        </div>
      );
  }
}
