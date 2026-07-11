import { useEffect, useState } from "react";
import { getCompliance, type ComplianceRow, type ReminderTier } from "../api";

function formatDate(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-US", { month: "short", day: "numeric" });
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
 * Fetches on MOUNT, not via polling. Because Parent/Operator are tab-switched
 * within one SPA (not two separate windows), switching to this tab unmounts
 * and remounts it each time — which is already "refetch on view." A parent's
 * acknowledge tap is visible the moment you switch to Operator.
 */
export default function Dashboard() {
  const [rows, setRows] = useState<ComplianceRow[] | null>(null);

  useEffect(() => {
    getCompliance().then(setRows);
  }, []);

  if (!rows) {
    return (
      <div className="text-sm" style={{ color: "var(--cubby-text-muted)" }}>
        Loading roster…
      </div>
    );
  }

  return (
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
  );
}
