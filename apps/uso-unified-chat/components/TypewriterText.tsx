"use client";

import { useState, useEffect } from "react";

type TypewriterTextProps = {
  text: string;
  speedMs?: number;
  enabled?: boolean;
  className?: string;
};

export function TypewriterText({
  text,
  speedMs = 30,
  enabled = true,
  className = "",
}: TypewriterTextProps) {
  const [displayed, setDisplayed] = useState("");
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (!enabled || !text) {
      setDisplayed(text ?? "");
      setDone(true);
      return;
    }
    setDisplayed("");
    setDone(false);
    let i = 0;
    const timer = setInterval(() => {
      i += 1;
      setDisplayed(text.slice(0, i));
      if (i >= text.length) {
        clearInterval(timer);
        setDone(true);
      }
    }, speedMs);
    return () => clearInterval(timer);
  }, [text, speedMs, enabled]);

  if (!enabled) {
    return <span className={className}>{text}</span>;
  }

  return (
    <span className={className}>
      {displayed}
      {!done && (
        <span
          className="inline-block w-0.5 h-4 ml-0.5 align-middle bg-current opacity-70 animate-pulse"
          aria-hidden
        />
      )}
    </span>
  );
}
