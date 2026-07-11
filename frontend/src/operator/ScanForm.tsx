import { useRef, useState } from "react";
import { validateForm, type ValidationResult } from "../api";

function formatDate(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" });
}

const VERDICT_STYLE: Record<ValidationResult["status"], { bg: string; border: string; label: string }> = {
  accepted: { bg: "var(--cubby-green-bg)", border: "var(--cubby-green)", label: "✅ Accepted" },
  rejected: { bg: "var(--cubby-red-bg)", border: "var(--cubby-red)", label: "❌ Rejected" },
  needs_review: { bg: "var(--cubby-amber-bg)", border: "var(--cubby-amber)", label: "⚠ Needs review" },
};

/**
 * Photo upload -> spinner -> verdict card. The "while the parent is standing
 * there" moment: a rejection comes back with a specific field + fix, not a
 * generic error. On accept, the roster is already updated server-side --
 * switching to the Compliance Dashboard shows the flip immediately.
 */
export default function ScanForm({ onAccepted }: { onAccepted?: () => void }) {
  const [result, setResult] = useState<ValidationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  async function onFile(file: File | undefined) {
    if (!file) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const r = await validateForm(file);
      setResult(r);
      if (r.status === "accepted") onAccepted?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong scanning that form.");
    } finally {
      setLoading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <div className="rounded-2xl p-4 shadow-sm mb-3" style={{ backgroundColor: "var(--cubby-surface)" }}>
      <div className="font-semibold text-sm mb-2" style={{ color: "var(--cubby-text)" }}>
        Scan Health Form
      </div>

      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        capture="environment"
        onChange={(e) => onFile(e.target.files?.[0])}
        className="hidden"
        id="scan-input"
      />
      <label
        htmlFor="scan-input"
        className="inline-block rounded-full px-4 py-2 text-sm font-semibold text-white cursor-pointer"
        style={{ backgroundColor: "var(--cubby-teal)" }}
      >
        📷 Take or choose a photo
      </label>

      {loading && (
        <div className="mt-3 text-sm" style={{ color: "var(--cubby-text-muted)" }}>
          Scanning…
        </div>
      )}

      {error && (
        <div
          className="mt-3 rounded-lg border p-3 text-sm"
          style={{ backgroundColor: "var(--cubby-error-bg)", borderColor: "var(--cubby-error-border)", color: "var(--cubby-error-text)" }}
        >
          {error}
        </div>
      )}

      {result && (
        <div
          className="mt-3 rounded-lg border p-3"
          style={{ backgroundColor: VERDICT_STYLE[result.status].bg, borderColor: VERDICT_STYLE[result.status].border }}
        >
          <div className="font-semibold text-sm" style={{ color: "var(--cubby-text)" }}>
            {VERDICT_STYLE[result.status].label}
          </div>

          {result.status === "accepted" && result.next_due_date && (
            <div className="mt-1 text-sm" style={{ color: "var(--cubby-text)" }}>
              Next report due {formatDate(result.next_due_date)}. Roster updated.
            </div>
          )}

          {result.issues.length > 0 && (
            <ul className="mt-2 flex flex-col gap-2">
              {result.issues.map((issue, i) => (
                <li key={i} className="text-sm" style={{ color: "var(--cubby-text)" }}>
                  <div>{issue.problem}</div>
                  <div className="text-xs mt-0.5" style={{ color: "var(--cubby-text-muted)" }}>
                    Fix: {issue.fix}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
