import { useEffect, useState } from "react";
import AccessGate from "./AccessGate";
import { checkAuthStatus } from "./api";
import Chat from "./parent/Chat";
import ReminderCard from "./parent/ReminderCard";
import ChildSwitcher from "./parent/ChildSwitcher";
import Dashboard from "./operator/Dashboard";
import ScanForm from "./operator/ScanForm";
import ThemeToggle from "./ThemeToggle";

type Tab = "parent" | "operator";

export default function App() {
  const [tab, setTab] = useState<Tab>("parent");
  const [childId, setChildId] = useState("reyes-sofia");
  // Bumped on an accepted scan so <Dashboard key=...> remounts and refetches
  // without needing a tab switch -- ScanForm and Dashboard share one view.
  const [dashboardKey, setDashboardKey] = useState(0);

  // null = checking; false = show the gate; true = render the app. The
  // probe itself no-ops server-side when no ACCESS_CODE is configured, so
  // local dev never sees this screen.
  const [authed, setAuthed] = useState<boolean | null>(null);
  useEffect(() => {
    checkAuthStatus().then(setAuthed);
  }, []);

  if (authed === null) {
    return (
      <div
        className="flex-1 flex items-center justify-center text-sm"
        style={{ color: "var(--cubby-text-muted)", backgroundColor: "var(--cubby-cream)" }}
      >
        Loading…
      </div>
    );
  }
  if (authed === false) {
    return <AccessGate onSuccess={() => setAuthed(true)} />;
  }

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
            <ChildSwitcher value={childId} onChange={setChildId} />
            <ReminderCard childId={childId} />
          </>
        ) : (
          <>
            <ScanForm onAccepted={() => setDashboardKey((k) => k + 1)} />
            <Dashboard key={dashboardKey} />
          </>
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
