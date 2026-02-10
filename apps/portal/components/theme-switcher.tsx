"use client";

import { useTheme } from "@/components/theme-provider";
import { Button } from "@/components/ui/button";

const themes = ["light", "dark", "ocean", "forest", "slate"] as const;

export function ThemeSwitcher() {
  const { theme, setTheme } = useTheme();

  return (
    <div className="flex flex-wrap gap-1">
      {themes.map((t) => (
        <Button
          key={t}
          variant={theme === t ? "default" : "outline"}
          size="sm"
          onClick={() => setTheme(t)}
        >
          {t}
        </Button>
      ))}
    </div>
  );
}
