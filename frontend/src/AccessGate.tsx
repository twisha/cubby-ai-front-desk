import { useState } from "react";
import { login } from "./api";

/**
 * Splash shown when the server's /api/auth/status probe returns 401. Real
 * enforcement is server-side (require_auth on every guarded route) — this
 * form is just the UX for obtaining the session cookie, not the security
 * boundary itself.
 */
export default function AccessGate({ onSuccess }: { onSuccess: () => void }) {
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await login(email, code);
      onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      className="flex-1 flex items-center justify-center p-6"
      style={{ backgroundColor: "var(--cubby-cream)" }}
    >
      <form
        onSubmit={submit}
        className="w-full max-w-sm rounded-2xl p-6 shadow-sm"
        style={{ backgroundColor: "var(--cubby-surface)" }}
      >
        <h1 className="text-xl font-bold m-0" style={{ color: "var(--cubby-text)" }}>
          🧸 Cubby
        </h1>
        <p className="text-sm mt-1 mb-4" style={{ color: "var(--cubby-text-muted)" }}>
          Enter your email and the access code you were given to view this
          prototype.
        </p>
        <input
          type="email"
          required
          placeholder="you@example.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full rounded-lg px-3 py-2 text-sm mb-2 outline-none"
          style={{ backgroundColor: "var(--cubby-surface-2)", color: "var(--cubby-text)" }}
        />
        <input
          type="password"
          required
          placeholder="Access code"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          className="w-full rounded-lg px-3 py-2 text-sm outline-none"
          style={{ backgroundColor: "var(--cubby-surface-2)", color: "var(--cubby-text)" }}
        />
        {error && (
          <div className="mt-2 text-sm" style={{ color: "var(--cubby-error-text)" }}>
            {error}
          </div>
        )}
        <button
          type="submit"
          disabled={loading}
          className="w-full mt-4 rounded-full py-2.5 font-semibold text-white disabled:opacity-40"
          style={{ backgroundColor: "var(--cubby-coral)" }}
        >
          {loading ? "Checking…" : "Enter"}
        </button>
      </form>
    </div>
  );
}
