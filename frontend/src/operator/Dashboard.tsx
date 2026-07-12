import { useEffect, useState } from "react";
import {
  getCompliance,
  getFlaggedForms,
  notifyParent,
  type ComplianceRow,
  type ReminderTier,
  type FlaggedForm,
} from "../api";

function formatDate(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
}

// SPEC's 4-chip palette: green/amber/amber-paused/red. The three "due soon"
// tiers (gentle/standard/urgent) plus paused/grace_requested all share the
// amber tone — differentiated by label text, not another color.
function chipColors(tier: ReminderTier): { bg: string; fg: string } {
  if (tier === "compliant") return { bg: "var(--cubby-green-bg)", fg: "var(--cubby-green)" };
  if (tier === "overdue") return { bg: "var(--cubby-red-bg)", fg: "var(--cubby-red)" };
  return { bg: "var(--cubby-amber-bg)", fg: "var(--cubby-amber)" };
}

function chipLabel(row: ComplianceRow): string {
  const { tier, days_until_due, child } = row;
  switch (tier) {
    case "compliant":
      return "Compliant";
    case "overdue":
      return `Overdue ${Math.abs(days_until_due ?? 0)}d`;
    case "urgent":
      return `Urgent — ${days_until_due}d`;
    case "standard":
      return `Due soon — ${days_until_due}d`;
    case "gentle":
      return `Heads up — ${days_until_due}d`;
    case "paused":
      return `Paused — appt ${child.acknowledged_appt_date ? formatDate(child.acknowledged_appt_date) : "?"}`;
    case "grace_requested":
      return "Grace requested — needs OK";
  }
}

/**
 * Flagged (rejected/needs_review) scans, persisted server-side so they're
 * still here after the upload card that produced them is gone. This is the
 * operator's actual queue — process forms in bulk elsewhere, then work the
 * list here: read the issue, notify the parent, done.
 */
function NeedsAttention({ items, onChange }: { items: FlaggedForm[]; onChange: () => void }) {
  const [notifying, setNotifying] = useState<string | null>(null);

  if (items.length === 0) return null;

  async function notify(id: string) {
    setNotifying(id);
    try {
      await notifyParent(id);
      onChange();
    } finally {
      setNotifying(null);
    }
  }

  return (
    <div className="flex flex-col gap-2 mb-4">
      <div className="font-semibold text-sm" style={{ color: "var(--cubby-text)" }}>
        Needs attention ({items.length})
      </div>
      {items.map((f) => (
        <div
          key={f.id}
          className="rounded-2xl p-3.5 shadow-sm"
          style={{
            backgroundColor: f.status === "rejected" ? "var(--cubby-red-bg)" : "var(--cubby-amber-bg)",
          }}
        >
          <div className="flex items-center justify-between gap-3">
            <div className="font-semibold text-sm" style={{ color: "var(--cubby-text)" }}>
              {f.child_name ?? "Unmatched scan"}
            </div>
            <span className="text-xs" style={{ color: "var(--cubby-text-muted)" }}>
              {formatTime(f.scanned_at)}
            </span>
          </div>
          <ul className="mt-1.5 flex flex-col gap-1">
            {f.issues.map((issue, i) => (
              <li key={i} className="text-xs" style={{ color: "var(--cubby-text)" }}>
                {issue.problem}
              </li>
            ))}
          </ul>

          {f.notified_at ? (
            <div className="mt-2 text-xs font-semibold" style={{ color: "var(--cubby-text-muted)" }}>
              ✅ Notified {f.parent_name} at {formatTime(f.notified_at)}
            </div>
          ) : f.parent_name ? (
            <button
              onClick={() => notify(f.id)}
              disabled={notifying === f.id}
              className="mt-2 rounded-full px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-40"
              style={{ backgroundColor: "var(--cubby-teal)" }}
            >
              {notifying === f.id ? "Notifying…" : `📣 Notify ${f.parent_name}`}
            </button>
          ) : (
            <div className="mt-2 text-xs" style={{ color: "var(--cubby-text-muted)" }}>
              No matching child on the roster — identify manually, then re-scan.
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

/**
 * Fetches on MOUNT, not via polling. Because Parent/Operator are tab-switched
 * within one SPA (not two separate windows), switching to this tab unmounts
 * and remounts it each time — which is already "refetch on view." A parent's
 * acknowledge tap, or a batch of scans, is visible the moment you switch to
 * Operator. This is the primary Operator view — scanning is a supporting
 * action that feeds it, not the other way around.
 */
export default function Dashboard() {
  const [rows, setRows] = useState<ComplianceRow[] | null>(null);
  const [flagged, setFlagged] = useState<FlaggedForm[] | null>(null);

  function refetch() {
    getCompliance().then(setRows);
    getFlaggedForms().then(setFlagged);
  }

  useEffect(refetch, []);

  if (!rows || !flagged) {
    return (
      <div className="text-sm" style={{ color: "var(--cubby-text-muted)" }}>
        Loading roster…
      </div>
    );
  }

  return (
    <div>
      <NeedsAttention items={flagged} onChange={refetch} />

      <div className="flex flex-col gap-2">
        {rows.map((r) => {
          const { bg, fg } = chipColors(r.tier);
          return (
            <div
              key={r.child.id}
              className="rounded-2xl p-3.5 shadow-sm flex items-center justify-between gap-3"
              style={{ backgroundColor: "var(--cubby-surface)" }}
            >
              <div>
                <div className="font-semibold text-sm" style={{ color: "var(--cubby-text)" }}>
                  {r.child.name}
                </div>
                <div className="text-xs" style={{ color: "var(--cubby-text-muted)" }}>
                  {r.cycle_months}-month cycle
                  {r.next_due_date && <> · due {formatDate(r.next_due_date)}</>}
                </div>
              </div>
              <span
                className="rounded-full px-2.5 py-1 text-xs font-semibold whitespace-nowrap"
                style={{ backgroundColor: bg, color: fg }}
              >
                {chipLabel(r)}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
