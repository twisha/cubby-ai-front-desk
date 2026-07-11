import { useState } from "react";
import Chat from "./parent/Chat";
import ReminderCard from "./parent/ReminderCard";
import Dashboard from "./operator/Dashboard";
import ThemeToggle from "./ThemeToggle";

type Tab = "parent" | "operator";

export default function App() {
  const [tab, setTab] = useState<Tab>("parent");

  return (
    <>
      <header
        className="px-5 py-4 text-white flex items-start justify-between"
        style={{ backgroundColor: "var(--cubby-teal)" }}
      >
        <div>
          <h1 className="m-0 text-xl font-bold">🧸 Cubby</h1>
          <p className="m-0 mt-1 text-sm opacity-85">
            Willow Grove Early Learning · Wissahocken, PA
          </p>
        </div>
        <ThemeToggle />
      </header>

      <nav
        className="flex gap-2 px-5 py-3 border-b"
        style={{ backgroundColor: "var(--cubby-surface)", borderColor: "var(--cubby-border)" }}
      >
        <TabButton active={tab === "parent"} onClick={() => setTab("parent")}>
          Parent
        </TabButton>
        <TabButton active={tab === "operator"} onClick={() => setTab("operator")}>
          Operator
        </TabButton>
      </nav>

      <main className="flex-1 px-4 py-4">
        {tab === "parent" ? (
          <>
            <Chat />
            <ReminderCard />
          </>
        ) : (
          <Dashboard />
        )}
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
      className="flex-1 rounded-xl py-2.5 font-semibold transition-colors"
      style={
        active
          ? { backgroundColor: "var(--cubby-coral)", color: "white" }
          : { backgroundColor: "var(--cubby-surface-2)", color: "var(--cubby-text)" }
      }
    >
      {children}
    </button>
  );
}
