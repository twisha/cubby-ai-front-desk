import { useEffect, useState } from "react";
import { getCompliance, type Child } from "../api";

/**
 * "Viewing as" selector — stands in for real per-parent login, which this
 * demo doesn't have (one shared access code for everyone). Lets you scan a
 * child's form on the Operator tab, then flip here to see that same child's
 * reminder card update.
 */
export default function ChildSwitcher({
  value,
  onChange,
}: {
  value: string;
  onChange: (childId: string) => void;
}) {
  const [children, setChildren] = useState<Child[]>([]);

  useEffect(() => {
    getCompliance().then((rows) => setChildren(rows.map((r) => r.child)));
  }, []);

  if (children.length === 0) return null;

  return (
    <div className="flex items-center gap-2 mb-3 text-sm">
      <span style={{ color: "var(--cubby-text-muted)" }}>Viewing as parent of</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-lg px-2 py-1 text-sm font-semibold"
        style={{ backgroundColor: "var(--cubby-surface)", color: "var(--cubby-text)" }}
      >
        {children.map((c) => (
          <option key={c.id} value={c.id}>
            {c.name}
          </option>
        ))}
      </select>
    </div>
  );
}
