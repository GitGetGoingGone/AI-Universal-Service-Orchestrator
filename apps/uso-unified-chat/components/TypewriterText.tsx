"use client";

import { useState, useEffect, type ReactNode } from "react";

type TypewriterTextProps = {
  text: string;
  speedMs?: number;
  enabled?: boolean;
  className?: string;
  /** When set, the displayed substring is rendered with this renderer (e.g. markdown). Otherwise plain text. */
  render?: (displayed: string) => ReactNode;
};

export function TypewriterText({
  text,
  speedMs = 30,
  enabled = true,
  className = "",
  render,
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
    const content = render ? render(text) : text;
    return <span className={className}>{content}</span>;
  }

  const content = render ? render(displayed) : displayed;
  return (
    <span className={className}>
      {content}
      {!done && (
        <span
          className="inline-block w-0.5 h-4 ml-0.5 align-middle bg-current opacity-70 animate-pulse"
          aria-hidden
        />
      )}
    </span>
  );
}
