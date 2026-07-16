import { useEffect, useState } from "react";
import { getGaps, type GapCategory, type GapGroup } from "../api";

function timeAgo(iso: string): string {
  const mins = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

function GroupCard({ g }: { g: GapGroup }) {
  return (
    <div className="rounded-2xl p-3.5 shadow-sm" style={{ backgroundColor: "var(--cubby-surface)" }}>
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
  );
}

const CATEGORY_LABEL: Record<GapCategory, string> = {
  content_gap: "Knowledge gaps",
  off_topic: "Off-topic / unrelated",
  unclear: "Unclear",
};

/**
 * Read-only view of parent questions Cubby couldn't answer, grouped by
 * shared keyword (backend/core/rules/gaps.py — no ML, no LLM: token-overlap
 * clustering, same philosophy as KeywordRetriever). M0.4b scope per
 * DESIGN.md: grouping only. The live "draft a handbook section from this
 * gap, approve, re-index" flywheel is M3, layered on top of this same
 * grouping later — this panel doesn't act on anything yet, it just surfaces
 * what parents keep asking that the handbook doesn't cover.
 *
 * `category` (Phase 1 sharpening) splits that single list into three
 * sections instead of one flat one: content gaps are the actionable
 * headline, off-topic/unclear questions are never hidden -- just collapsed
 * by default so they don't compete for attention with what's actually
 * worth adding to the handbook.
 */
export default function GapsPanel() {
  const [groups, setGroups] = useState<GapGroup[] | null>(null);

  useEffect(() => {
    getGaps().then(setGroups);
  }, []);

  if (!groups || groups.length === 0) return null;

  const contentGaps = groups.filter((g) => g.category === "content_gap");
  const lowSignal = groups.filter((g) => g.category !== "content_gap");

  return (
    <div className="flex flex-col gap-2 mb-4">
      <div className="font-semibold text-sm" style={{ color: "var(--cubby-text)" }}>
        {CATEGORY_LABEL.content_gap}
      </div>
      {contentGaps.length === 0 && (
        <div className="text-xs" style={{ color: "var(--cubby-text-muted)" }}>
          No open content gaps right now.
        </div>
      )}
      {contentGaps.map((g) => (
        <GroupCard key={g.theme} g={g} />
      ))}

      {lowSignal.length > 0 && (
        <details className="mt-2">
          <summary
            className="text-xs font-semibold cursor-pointer select-none"
            style={{ color: "var(--cubby-text-muted)" }}
          >
            {lowSignal.length} off-topic / unclear question{lowSignal.length === 1 ? "" : "s"}
          </summary>
          <div className="flex flex-col gap-2 mt-2">
            {(["off_topic", "unclear"] as GapCategory[]).map((cat) => {
              const inCat = lowSignal.filter((g) => g.category === cat);
              if (inCat.length === 0) return null;
              return (
                <div key={cat} className="flex flex-col gap-2">
                  <div className="text-xs font-semibold" style={{ color: "var(--cubby-text-muted)" }}>
                    {CATEGORY_LABEL[cat]}
                  </div>
                  {inCat.map((g) => (
                    <GroupCard key={g.theme} g={g} />
                  ))}
                </div>
              );
            })}
          </div>
        </details>
      )}
    </div>
  );
}
