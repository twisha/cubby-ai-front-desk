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
