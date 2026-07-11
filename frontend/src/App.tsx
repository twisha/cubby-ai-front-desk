import { useState } from "react";
import Chat from "./parent/Chat";

type Tab = "parent" | "operator";

export default function App() {
  const [tab, setTab] = useState<Tab>("parent");

  return (
    <>
      <header
        className="px-5 py-4 text-white"
        style={{ backgroundColor: "var(--cubby-teal)" }}
      >
        <h1 className="m-0 text-xl font-bold">🧸 Cubby</h1>
        <p className="m-0 mt-1 text-sm opacity-85">
          Willow Grove Early Learning · Wissahocken, PA
        </p>
      </header>

      <nav className="flex gap-2 px-5 py-3 bg-white border-b border-[#eadfd6]">
        <TabButton active={tab === "parent"} onClick={() => setTab("parent")}>
          Parent
        </TabButton>
        <TabButton active={tab === "operator"} onClick={() => setTab("operator")}>
          Operator
        </TabButton>
      </nav>

      <main className="flex-1 px-4 py-4">
        {tab === "parent" ? <Chat /> : <OperatorPlaceholder />}
      </main>
    </>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex-1 rounded-xl py-2.5 font-semibold transition-colors ${
        active ? "text-white" : "bg-[#f2e7de] text-[#26333a]"
      }`}
      style={active ? { backgroundColor: "var(--cubby-coral)" } : undefined}
    >
      {children}
    </button>
  );
}

function OperatorPlaceholder() {
  return (
    <div className="rounded-2xl bg-white p-5 shadow-sm text-sm text-[#26333a]/80">
      <b>Operator tab</b> — health form scan, compliance dashboard, and the
      questions &amp; gaps log arrive in M0.2–M0.4.
    </div>
  );
}
