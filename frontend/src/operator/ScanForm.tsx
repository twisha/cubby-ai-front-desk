import { useRef, useState } from "react";
import { validateForms, type BatchScanItem } from "../api";

/**
 * Bulk photo upload -> spinner -> compact per-file summary. This is
 * deliberately NOT the primary Operator view — it's the ingestion step that
 * feeds the Dashboard below. Drop in a whole batch of forms at once; accepted
 * ones flip on the roster immediately, anything rejected or unclear lands in
 * the Dashboard's "Needs attention" queue for follow-up. The operator's job
 * is to watch that queue, not babysit each individual scan.
 */
export default function ScanForm({ onProcessed }: { onProcessed?: () => void }) {
  const [items, setItems] = useState<BatchScanItem[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  async function onFiles(files: FileList | null) {
    if (!files || files.length === 0) return;
    setLoading(true);
    setError(null);
    setItems(null);
    try {
      const results = await validateForms(Array.from(files));
      setItems(results);
      onProcessed?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong processing those forms.");
    } finally {
      setLoading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  const accepted = items?.filter((i) => i.result.status === "accepted").length ?? 0;
  const flagged = items ? items.length - accepted : 0;

  return (
    <div className="rounded-2xl p-4 shadow-sm mb-3" style={{ backgroundColor: "var(--cubby-surface)" }}>
      <div className="font-semibold text-sm mb-2" style={{ color: "var(--cubby-text)" }}>
        Process Health Forms
      </div>

      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        capture="environment"
        multiple
        onChange={(e) => onFiles(e.target.files)}
        className="hidden"
        id="scan-input"
      />
      <label
        htmlFor="scan-input"
        className="inline-block rounded-full px-4 py-2 text-sm font-semibold text-white cursor-pointer"
        style={{ backgroundColor: "var(--cubby-teal)" }}
      >
        📷 Take or choose photos
      </label>

      {loading && (
        <div className="mt-3 text-sm" style={{ color: "var(--cubby-text-muted)" }}>
          Processing…
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

      {items && (
        <div className="mt-3">
          <div className="text-sm font-semibold mb-1.5" style={{ color: "var(--cubby-text)" }}>
            Processed {items.length}: {accepted} accepted, {flagged} need attention — see the dashboard below.
          </div>
          <ul className="flex flex-col gap-1">
            {items.map((item, i) => (
              <li key={i} className="text-xs flex items-center gap-2" style={{ color: "var(--cubby-text-muted)" }}>
                <span>{item.result.status === "accepted" ? "✅" : item.result.status === "rejected" ? "❌" : "⚠"}</span>
                <span>{item.child_name ?? item.filename}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
