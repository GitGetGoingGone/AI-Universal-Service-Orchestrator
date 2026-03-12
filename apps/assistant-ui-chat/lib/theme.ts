export type ThemeId = "spring" | "summer" | "autumn" | "winter";

export const THEMES: Record<
  ThemeId,
  {
    primary: string;
    primaryForeground: string;
    background: string;
    foreground: string;
    card: string;
    cardForeground: string;
    muted: string;
    border: string;
    sidebar: string;
    sidebarForeground: string;
  }
> = {
  spring: {
    primary: "#22c55e",
    primaryForeground: "#fff",
    background: "#0f172a",
    foreground: "#f8fafc",
    card: "#1e293b",
    cardForeground: "#e2e8f0",
    muted: "#334155",
    border: "#334155",
    sidebar: "#0f172a",
    sidebarForeground: "#f8fafc",
  },
  summer: {
    primary: "#f59e0b",
    primaryForeground: "#fff",
    background: "#0f172a",
    foreground: "#fef3c7",
    card: "#1e293b",
    cardForeground: "#fef3c7",
    muted: "#64748b",
    border: "#475569",
    sidebar: "#0f172a",
    sidebarForeground: "#fef3c7",
  },
  autumn: {
    primary: "#ea580c",
    primaryForeground: "#fff",
    background: "#1c1917",
    foreground: "#fef3c7",
    card: "#292524",
    cardForeground: "#e7e5e4",
    muted: "#78716c",
    border: "#44403c",
    sidebar: "#1c1917",
    sidebarForeground: "#fef3c7",
  },
  winter: {
    primary: "#0ea5e9",
    primaryForeground: "#fff",
    background: "#0f172a",
    foreground: "#f8fafc",
    card: "#1e293b",
    cardForeground: "#e2e8f0",
    muted: "#334155",
    border: "#334155",
    sidebar: "#0f172a",
    sidebarForeground: "#f8fafc",
  },
};

const STORAGE_KEY = "assistant_ui_theme";

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
  root.style.setProperty("--primary", t.primary);
  root.style.setProperty("--primary-foreground", t.primaryForeground);
  root.style.setProperty("--background", t.background);
  root.style.setProperty("--foreground", t.foreground);
  root.style.setProperty("--card", t.card);
  root.style.setProperty("--card-foreground", t.cardForeground);
  root.style.setProperty("--muted", t.muted);
  root.style.setProperty("--border", t.border);
  root.style.setProperty("--sidebar", t.sidebar);
  root.style.setProperty("--sidebar-foreground", t.sidebarForeground);
}
