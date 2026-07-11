import { useEffect, useState } from "react";

type Theme = "light" | "dark";

function systemPrefersDark(): boolean {
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

function currentTheme(): Theme {
  const attr = document.documentElement.getAttribute("data-theme");
  if (attr === "light" || attr === "dark") return attr;
  return systemPrefersDark() ? "dark" : "light";
}

/** Sun/moon toggle. Persists an explicit choice to localStorage (read
 * pre-React in index.html to avoid a flash); with no saved choice, the
 * system's prefers-color-scheme governs via CSS alone. */
export default function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(currentTheme);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("cubby-theme", theme);
  }, [theme]);

  return (
    <button
      onClick={() => setTheme((t) => (t === "dark" ? "light" : "dark"))}
      aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
      className="rounded-full w-8 h-8 flex items-center justify-center text-white/90 hover:bg-white/15 transition-colors"
    >
      {theme === "dark" ? "☀️" : "🌙"}
    </button>
  );
}
