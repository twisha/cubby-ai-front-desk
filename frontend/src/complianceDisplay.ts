// Shared between Dashboard.tsx (Operator) and ReminderCard.tsx (Parent) so
// the same child's urgency reads identically on both tabs — same label,
// same color. Previously each tab formatted dates/tiers independently and
// neither included the year, so "due Jun 1" (compliant, 11 months out) and
// "due Jun 20" (overdue by 3 weeks) looked equally urgent at a glance.
import type { ComplianceRow, ReminderTier } from "./api";

export function formatDueDate(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

// SPEC's 4-chip palette: green/amber/amber-paused/red. The three "due soon"
// tiers (gentle/standard/urgent) plus paused/grace_requested all share the
// amber tone — differentiated by label text, not another color.
export function chipColors(tier: ReminderTier): { bg: string; fg: string } {
  if (tier === "compliant") return { bg: "var(--cubby-green-bg)", fg: "var(--cubby-green)" };
  if (tier === "overdue") return { bg: "var(--cubby-red-bg)", fg: "var(--cubby-red)" };
  return { bg: "var(--cubby-amber-bg)", fg: "var(--cubby-amber)" };
}

export function chipLabel(row: ComplianceRow): string {
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
      return `Paused — appt ${child.acknowledged_appt_date ? formatDueDate(child.acknowledged_appt_date) : "?"}`;
    case "grace_requested":
      return "Grace requested — needs OK";
  }
}
