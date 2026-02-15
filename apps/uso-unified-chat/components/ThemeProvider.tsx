"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import {
  type ThemeId,
  getStoredTheme,
  setStoredTheme,
  applyTheme,
} from "@/lib/theme";

type ThemeContextValue = { theme: ThemeId; setTheme: (id: ThemeId) => void };
const ThemeContext = createContext<ThemeContextValue | null>(null);

export function useTheme() {
  const ctx = useContext(ThemeContext);
  return ctx ?? { theme: "winter" as ThemeId, setTheme: () => {} };
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<ThemeId>("winter");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const stored = getStoredTheme();
    setThemeState(stored);
    applyTheme(stored);
  }, []);

  const setTheme = (id: ThemeId) => {
    setThemeState(id);
    setStoredTheme(id);
    applyTheme(id);
  };

  if (!mounted) return <>{children}</>;

  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}
