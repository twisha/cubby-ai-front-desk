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
  parent_name: string;
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

// --- Gaps panel (mirrors backend/models/ask.py's GapGroup) ---

export type AnswerModeLog = "grounded" | "judgment" | "escalated" | "gap";

export interface QuestionLog {
  id: string;
  ts: string;
  text: string;
  mode: AnswerModeLog;
  max_cosine: number;
  source_ids: string[];
  answer: string | null;
}

export interface GapGroup {
  theme: string;
  count: number;
  questions: QuestionLog[];
}

export async function getGaps(): Promise<GapGroup[]> {
  const res = await fetch("/api/gaps");
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

export interface BatchScanItem {
  filename: string;
  child_name: string | null;
  result: ValidationResult;
}

/** Bulk scan: one request, any number of photos. Accepted ones update the
 * roster server-side; rejected/needs_review ones are persisted as
 * FlaggedForm and surface on the Dashboard's "Needs attention" list. */
export async function validateForms(files: File[]): Promise<BatchScanItem[]> {
  const body = new FormData();
  for (const f of files) body.append("photos", f);
  const res = await fetch("/api/validate-form", { method: "POST", body });
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail ?? `Request failed (${res.status})`);
  }
  return res.json();
}

export interface FlaggedForm {
  id: string;
  child_id: string | null;
  child_name: string | null;
  parent_name: string | null;
  status: "rejected" | "needs_review";
  issues: ValidationIssue[];
  scanned_at: string;
  notified_at: string | null;
}

export async function getFlaggedForms(): Promise<FlaggedForm[]> {
  const res = await fetch("/api/flagged-forms");
  if (!res.ok) throw new Error(`Request failed (${res.status})`);
  return res.json();
}

export async function notifyParent(flagId: string): Promise<FlaggedForm> {
  const res = await fetch(`/api/flagged-forms/${flagId}/notify`, { method: "POST" });
  if (!res.ok) throw new Error(`Request failed (${res.status})`);
  return res.json();
}

export interface AssignResult {
  resolved: boolean;
  flagged: FlaggedForm | null;
  next_due_date: string | null;
}

/** Resolve an unmatched scan by picking the right child -- re-validates the
 * same extracted data server-side, no re-scan needed. */
export async function assignChild(flagId: string, childId: string): Promise<AssignResult> {
  const res = await fetch(`/api/flagged-forms/${flagId}/assign`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ child_id: childId }),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail ?? `Request failed (${res.status})`);
  }
  return res.json();
}

// --- Access gate (mirrors backend/models/auth.py) ---

/** True if already authed (or no gate is configured); false -> show AccessGate. */
export async function checkAuthStatus(): Promise<boolean> {
  const res = await fetch("/api/auth/status");
  return res.ok;
}

export async function login(email: string, code: string): Promise<void> {
  const res = await fetch("/api/auth", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ email, code }),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail ?? "That code doesn't match.");
  }
}
