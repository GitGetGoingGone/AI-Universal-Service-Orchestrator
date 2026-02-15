export type ThemeId = "spring" | "summer" | "autumn" | "winter";

export const THEMES: Record<
  ThemeId,
  {
    primary: string;
    background: string;
    foreground: string;
    card: string;
    cardForeground: string;
    muted: string;
    border: string;
  }
> = {
  spring: {
    primary: "#22c55e",
    background: "#0f172a",
    foreground: "#f8fafc",
    card: "#1e293b",
    cardForeground: "#e2e8f0",
    muted: "#334155",
    border: "#334155",
  },
  summer: {
    primary: "#f59e0b",
    background: "#0f172a",
    foreground: "#fef3c7",
    card: "#1e293b",
    cardForeground: "#fef3c7",
    muted: "#64748b",
    border: "#475569",
  },
  autumn: {
    primary: "#ea580c",
    background: "#1c1917",
    foreground: "#fef3c7",
    card: "#292524",
    cardForeground: "#e7e5e4",
    muted: "#78716c",
    border: "#44403c",
  },
  winter: {
    primary: "#0ea5e9",
    background: "#0f172a",
    foreground: "#f8fafc",
    card: "#1e293b",
    cardForeground: "#e2e8f0",
    muted: "#334155",
    border: "#334155",
  },
};

const STORAGE_KEY = "uso_theme";

export function getStoredTheme(): ThemeId {
  if (typeof window === "undefined") return "summer";
  const v = localStorage.getItem(STORAGE_KEY) as ThemeId | null;
  return v && THEMES[v] ? v : "summer";
}

export function setStoredTheme(id: ThemeId): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(STORAGE_KEY, id);
}

export function applyTheme(id: ThemeId): void {
  const t = THEMES[id];
  if (!t) return;
  const root = document.documentElement;
  root.style.setProperty("--primary-color", t.primary);
  root.style.setProperty("--background", t.background);
  root.style.setProperty("--foreground", t.foreground);
  root.style.setProperty("--card", t.card);
  root.style.setProperty("--card-foreground", t.cardForeground);
  root.style.setProperty("--muted", t.muted);
  root.style.setProperty("--border", t.border);
}
