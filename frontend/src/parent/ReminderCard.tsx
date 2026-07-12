import { useEffect, useState } from "react";
import { getCompliance, acknowledge, type ComplianceRow } from "../api";

// Demo has one parent view, no auth; production resolves this from the
// logged-in parent's session -> their child's roster row. Sofia starts
// "urgent", so tapping acknowledge produces a visible before/after flip on
// both tabs — the cross-feature money shot.
const DEMO_CHILD_ID = "reyes-sofia";

function formatDate(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-US", { month: "long", day: "numeric" });
}

function cycleLabel(months: number): string {
  return months === 6
    ? "6-month cycle for infants and young toddlers under 2"
    : "12-month cycle for toddlers and preschoolers 2 and up";
}

/**
 * Answers the four confusions a plain reminder letter raises (per the design
 * doc's parent-trust requirements): why now (due date + tier), can I use
 * records I have (health-report vs. immunization distinction), can I get an
 * extension (acknowledge -> pause, or grace-request if the appt is after the
 * due date), and what's the actual rule (cited).
 */
export default function ReminderCard() {
  const [row, setRow] = useState<ComplianceRow | null>(null);
  const [showPicker, setShowPicker] = useState(false);
  const [apptDate, setApptDate] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    getCompliance().then((rows) => {
      const mine = rows.find((r) => r.child.id === DEMO_CHILD_ID);
      if (mine) setRow(mine);
    });
  }, []);

  if (!row || !row.next_due_date) return null;

  async function confirm() {
    if (!apptDate) return;
    setSaving(true);
    try {
      const updated = await acknowledge(DEMO_CHILD_ID, apptDate);
      setRow(updated);
      setShowPicker(false);
    } finally {
      setSaving(false);
    }
  }

  const { tier, child } = row;
  const paused = tier === "paused";
  const graceRequested = tier === "grace_requested";
  const firstName = child.name.split(" ")[0];

  return (
    <div className="rounded-2xl p-4 shadow-sm mt-4" style={{ backgroundColor: "var(--cubby-surface)" }}>
      <p className="m-0 text-[15px] leading-snug" style={{ color: "var(--cubby-text)" }}>
        {firstName}'s health report expires <b>{formatDate(row.next_due_date)}</b> (
        {cycleLabel(row.cycle_months)}, 55 Pa. Code §3270.131(b)). Her next well
        visit generates the new form.
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
          ✓ Reminders paused — appt {formatDate(child.acknowledged_appt_date!)}
        </div>
      )}
      {graceRequested && (
        <div
          className="mt-3 rounded-lg px-3 py-2 text-xs font-semibold"
          style={{ backgroundColor: "var(--cubby-amber-bg)", color: "var(--cubby-amber)" }}
        >
          ⏳ Appointment noted for {formatDate(child.acknowledged_appt_date!)} — since
          that's after the due date, Ms. Donnelly will confirm it's okay.
        </div>
      )}

      {!paused && !graceRequested && !showPicker && (
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
