import { useEffect, useState } from "react";
import { getCompliance, acknowledge, type ComplianceRow } from "../api";
import { formatDueDate, chipColors, chipLabel } from "../complianceDisplay";

function cycleLabel(months: number): string {
  return months === 6
    ? "6-month cycle for infants and young toddlers under 2"
    : "12-month cycle for toddlers and preschoolers 2 and up";
}

// Same tier -> label/color mapping as the Operator Dashboard (see
// complianceDisplay.ts), so "overdue" and "compliant" don't read as the same
// calm, neutral message with a matching year-less date — that ambiguity is
// exactly what let a child overdue this month and one due 11 months out look
// identical on this card.
function headline(row: ComplianceRow, firstName: string): string {
  const date = formatDueDate(row.next_due_date!);
  const cycle = cycleLabel(row.cycle_months);
  const citation = `${cycle}, 55 Pa. Code §3270.131(b)`;
  switch (row.tier) {
    case "overdue":
      return `${firstName}'s health report was due ${date} — now ${Math.abs(row.days_until_due ?? 0)} days overdue (${citation}).`;
    case "compliant":
      return `${firstName} is all set. Next health report due ${date} (${citation}).`;
    default:
      return `${firstName}'s health report expires ${date} (${citation}). Their next well visit generates the new form.`;
  }
}

/**
 * Answers the four confusions a plain reminder letter raises (per the design
 * doc's parent-trust requirements): why now (due date + tier), can I use
 * records I have (health-report vs. immunization distinction), can I get an
 * extension (acknowledge -> pause, or grace-request if the appt is after the
 * due date), and what's the actual rule (cited).
 *
 * No real per-parent auth in this demo — one shared access code for
 * everyone — so `childId` is a client-side "view as" choice (see
 * ChildSwitcher), not a login. Acknowledging mutates the one shared
 * in-memory store, same as every other action in the app.
 */
export default function ReminderCard({ childId }: { childId: string }) {
  const [row, setRow] = useState<ComplianceRow | null>(null);
  const [showPicker, setShowPicker] = useState(false);
  const [apptDate, setApptDate] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setRow(null);
    setShowPicker(false);
    setApptDate("");
    getCompliance().then((rows) => {
      const mine = rows.find((r) => r.child.id === childId);
      if (mine) setRow(mine);
    });
  }, [childId]);

  if (!row || !row.next_due_date) return null;

  async function confirm() {
    if (!apptDate) return;
    setSaving(true);
    try {
      const updated = await acknowledge(childId, apptDate);
      setRow(updated);
      setShowPicker(false);
    } finally {
      setSaving(false);
    }
  }

  const { tier, child } = row;
  const paused = tier === "paused";
  const graceRequested = tier === "grace_requested";
  const compliant = tier === "compliant";
  const firstName = child.name.split(" ")[0];
  const { bg, fg } = chipColors(tier);

  return (
    <div className="rounded-2xl p-4 shadow-sm mt-4" style={{ backgroundColor: "var(--cubby-surface)" }}>
      <span
        className="inline-block rounded-full px-2.5 py-1 text-xs font-semibold whitespace-nowrap mb-2"
        style={{ backgroundColor: bg, color: fg }}
      >
        {chipLabel(row)}
      </span>

      <p className="m-0 text-[15px] leading-snug" style={{ color: "var(--cubby-text)" }}>
        {headline(row, firstName)}
      </p>
      <p className="m-0 mt-2 text-xs" style={{ color: "var(--cubby-text-muted)" }}>
        This is separate from immunizations — those are cumulative
        (§3270.131(e)-(f)), so an older immunization record can still be fully
        compliant.
      </p>

      {paused && (
        <div
          className="mt-3 rounded-lg px-3 py-2 text-xs font-semibold"
          style={{ backgroundColor: "var(--cubby-amber-bg)", color: "var(--cubby-amber)" }}
        >
          ✓ Reminders paused — appt {formatDueDate(child.acknowledged_appt_date!)}
        </div>
      )}
      {graceRequested && (
        <div
          className="mt-3 rounded-lg px-3 py-2 text-xs font-semibold"
          style={{ backgroundColor: "var(--cubby-amber-bg)", color: "var(--cubby-amber)" }}
        >
          ⏳ Appointment noted for {formatDueDate(child.acknowledged_appt_date!)} — since
          that's after the due date, Ms. Donnelly will confirm it's okay.
        </div>
      )}

      {/* Nothing to acknowledge yet for a compliant child months out --
          the CTA only makes sense once there's an upcoming report to plan
          around. */}
      {!paused && !graceRequested && !compliant && !showPicker && (
        <button
          onClick={() => setShowPicker(true)}
          className="mt-3 rounded-full px-4 py-2 text-sm font-semibold text-white"
          style={{ backgroundColor: "var(--cubby-teal)" }}
        >
          📅 We have an appointment
        </button>
      )}

      {showPicker && (
        <div className="mt-3 flex gap-2">
          <input
            type="date"
            value={apptDate}
            onChange={(e) => setApptDate(e.target.value)}
            className="flex-1 rounded-lg px-3 py-2 text-sm"
            style={{ backgroundColor: "var(--cubby-surface-2)", color: "var(--cubby-text)" }}
          />
          <button
            onClick={confirm}
            disabled={!apptDate || saving}
            className="rounded-full px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
            style={{ backgroundColor: "var(--cubby-coral)" }}
          >
            Confirm
          </button>
        </div>
      )}
    </div>
  );
}
