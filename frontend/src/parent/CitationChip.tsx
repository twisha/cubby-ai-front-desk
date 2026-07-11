import { useState } from "react";
import type { Source } from "../api";

/** Tap a citation chip -> the cited policy text expands inline below it.
 * "Parent Handbook → {Section Title}" per the SPEC's citation-chip copy. */
export default function CitationChip({ source }: { source: Source }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="inline-block align-top mr-1.5 mb-1.5">
      <button
        onClick={() => setOpen((o) => !o)}
        className="text-xs font-medium rounded-full px-2.5 py-1 border transition-colors"
        style={{
          borderColor: "var(--cubby-teal)",
          color: open ? "white" : "var(--cubby-teal)",
          backgroundColor: open ? "var(--cubby-teal)" : "transparent",
        }}
      >
        Parent Handbook → {source.title}
      </button>
      {open && (
        <div className="mt-1 max-w-xs text-xs leading-snug rounded-lg bg-[#f2e7de] p-2.5 text-[#26333a]">
          {source.content}
        </div>
      )}
    </div>
  );
}
