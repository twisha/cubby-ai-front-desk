// Typed fetch wrappers mirroring the backend's Pydantic response shapes
// (backend/routers/ask.py). The frontend never re-derives a routing decision —
// `mode` is exactly what /api/ask already decided; components only render it.

export type AnswerMode = "grounded" | "judgment" | "escalated" | "gap";

export interface Source {
  id: string;
  title: string;
  content: string;
}

export interface AskResponse {
  answer: string;
  mode: AnswerMode;
  confidence: string | null;
  sources: Source[];
  max_score: number;
  needs_human_judgment: boolean;
  sensitive: boolean;
}

export class AskError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export async function askQuestion(question: string): Promise<AskResponse> {
  const res = await fetch("/api/ask", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new AskError(
      detail?.detail ?? `Request failed (${res.status})`,
      res.status,
    );
  }
  return res.json();
}

// --- Compliance / roster (mirrors backend/models/roster.py + routers/compliance.py) ---

export type ParentState =
  | "compliant"
  | "due_soon_acknowledged"
  | "due_soon_unresponsive"
  | "overdue";

export type ReminderTier =
  | "compliant"
  | "gentle"
  | "standard"
  | "urgent"
  | "overdue"
  | "paused"
  | "grace_requested";

export interface Child {
  id: string;
  name: string;
  dob: string;
  last_exam_date: string | null;
  parent_state: ParentState;
  acknowledged_appt_date: string | null;
}

export interface ComplianceRow {
  child: Child;
  cycle_months: number;
  next_due_date: string | null;
  tier: ReminderTier;
  days_until_due: number | null;
}

export async function getCompliance(): Promise<ComplianceRow[]> {
  const res = await fetch("/api/compliance");
  if (!res.ok) throw new Error(`Request failed (${res.status})`);
  return res.json();
}

export async function acknowledge(
  childId: string,
  apptDate: string,
): Promise<ComplianceRow> {
  const res = await fetch("/api/acknowledge", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ child_id: childId, appt_date: apptDate }),
  });
  if (!res.ok) throw new Error(`Request failed (${res.status})`);
  return res.json();
}

// --- Health-form validation (mirrors backend/models/forms.py) ---

export interface ValidationIssue {
  field: string;
  problem: string;
  fix: string;
}

export interface ValidationResult {
  status: "accepted" | "rejected" | "needs_review";
  issues: ValidationIssue[];
  next_due_date: string | null;
}

export async function validateForm(file: File): Promise<ValidationResult> {
  const body = new FormData();
  body.append("photo", file);
  const res = await fetch("/api/validate-form", { method: "POST", body });
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail ?? `Request failed (${res.status})`);
  }
  return res.json();
}
