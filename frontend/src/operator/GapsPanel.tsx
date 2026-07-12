import { useEffect, useState } from "react";
import { getGaps, type GapGroup } from "../api";

function timeAgo(iso: string): string {
  const mins = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

/**
 * Read-only view of parent questions Cubby couldn't answer, grouped by
 * shared keyword (backend/core/rules/gaps.py — no ML, no LLM: token-overlap
 * clustering, same philosophy as KeywordRetriever). M0.4b scope per
 * DESIGN.md: grouping only. The live "draft a handbook section from this
 * gap, approve, re-index" flywheel is M3, layered on top of this same
 * grouping later — this panel doesn't act on anything yet, it just surfaces
 * what parents keep asking that the handbook doesn't cover.
 */
export default function GapsPanel() {
  const [groups, setGroups] = useState<GapGroup[] | null>(null);

  useEffect(() => {
    getGaps().then(setGroups);
  }, []);

  if (!groups || groups.length === 0) return null;

  return (
    <div className="flex flex-col gap-2 mb-4">
      <div className="font-semibold text-sm" style={{ color: "var(--cubby-text)" }}>
        Knowledge gaps
      </div>
      {groups.map((g) => (
        <div
          key={g.theme}
          className="rounded-2xl p-3.5 shadow-sm"
          style={{ backgroundColor: "var(--cubby-surface)" }}
        >
          <div className="flex items-center justify-between gap-3">
            <div className="font-semibold text-sm" style={{ color: "var(--cubby-text)" }}>
              {g.theme}
            </div>
            <span
              className="rounded-full px-2.5 py-1 text-xs font-semibold whitespace-nowrap"
              style={{ backgroundColor: "var(--cubby-amber-bg)", color: "var(--cubby-amber)" }}
            >
              {g.count} question{g.count === 1 ? "" : "s"}
            </span>
          </div>
          <ul className="mt-1.5 flex flex-col gap-1">
            {g.questions.map((q) => (
              <li
                key={q.id}
                className="text-xs flex items-baseline justify-between gap-2"
                style={{ color: "var(--cubby-text-muted)" }}
              >
                <span>"{q.text}"</span>
                <span className="whitespace-nowrap">{timeAgo(q.ts)}</span>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}
