import { useState } from "react";
import { askQuestion, AskError, type AskResponse } from "../api";
import AnswerBubble from "./AnswerBubble";

const SUGGESTED_CHIPS = [
  "Are you open on Veterans Day?",
  "What's infant tuition?",
  "My kid had a fever last night — can she come in?",
  "How do I schedule a tour?",
];

interface Turn {
  question: string;
  response?: AskResponse;
  error?: string;
}

export default function Chat() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  async function send(question: string) {
    const q = question.trim();
    if (!q || loading) return;
    setInput("");
    setLoading(true);
    setTurns((t) => [...t, { question: q }]);
    try {
      const response = await askQuestion(q);
      setTurns((t) => [...t.slice(0, -1), { question: q, response }]);
    } catch (e) {
      const msg =
        e instanceof AskError
          ? e.status === 503
            ? "Cubby's brain isn't configured yet — add ANTHROPIC_API_KEY to .env."
            : e.message
          : "Something went wrong reaching Cubby. Please try again.";
      setTurns((t) => [...t.slice(0, -1), { question: q, error: msg }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col gap-3">
      {turns.length === 0 && (
        <div className="flex flex-wrap gap-2">
          {SUGGESTED_CHIPS.map((chip) => (
            <button
              key={chip}
              onClick={() => send(chip)}
              className="text-sm rounded-full px-3 py-2 bg-white shadow-sm text-left"
              style={{ color: "var(--cubby-ink)" }}
            >
              {chip}
            </button>
          ))}
        </div>
      )}

      <div className="flex flex-col gap-3">
        {turns.map((turn, i) => (
          <div key={i} className="flex flex-col gap-1.5">
            <div className="self-end max-w-[85%] rounded-2xl rounded-br-sm bg-[#0f766e] text-white px-3.5 py-2.5 text-[15px]">
              {turn.question}
            </div>
            {turn.response && <AnswerBubble response={turn.response} />}
            {turn.error && (
              <div className="rounded-2xl bg-red-50 border border-red-200 p-3 text-sm text-red-800">
                {turn.error}
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="rounded-2xl bg-white p-3.5 shadow-sm text-sm text-[#26333a]/60">
            Cubby is checking the handbook…
          </div>
        )}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
        className="flex gap-2 sticky bottom-3 mt-1"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question…"
          className="flex-1 rounded-full bg-white px-4 py-2.5 text-[15px] shadow-sm outline-none"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="rounded-full px-4 py-2.5 font-semibold text-white disabled:opacity-40"
          style={{ backgroundColor: "var(--cubby-coral)" }}
        >
          Ask
        </button>
      </form>
    </div>
  );
}
