"use client";

import { useMemo, useState } from "react";
import { useAuiState } from "@assistant-ui/react";
import { ChevronRight } from "lucide-react";

function extractUserText(content: unknown): string {
  if (typeof content === "string") return content.trim();
  if (Array.isArray(content)) {
    return content
      .map((p: { type?: string; text?: string }) =>
        p?.type === "text" && typeof p?.text === "string" ? p.text : ""
      )
      .join("")
      .trim();
  }
  return "";
}

/**
 * User turn prompt: short preview with fade, tap to expand (reference-style chat UX).
 */
export function UserPromptCard() {
  const content = useAuiState((s) => s.message.content);
  const text = useMemo(() => extractUserText(content), [content]);
  const [expanded, setExpanded] = useState(false);

  if (!text) {
    return (
      <div className="w-full min-w-0">
        <div className="text-sm text-[var(--muted)]">(empty message)</div>
      </div>
    );
  }

  const long = text.length > 200 || text.includes("\n");

  const body = (
    <div className="whitespace-pre-wrap break-words text-[13px] leading-relaxed text-[var(--foreground)]">{text}</div>
  );

  return (
    <div className="w-full min-w-0 select-text">
      <div
        className={`rounded-lg border border-[var(--border)] bg-[var(--muted)]/40 transition-shadow dark:bg-[var(--muted)]/25 ${
          expanded ? "shadow-sm" : ""
        }`}
      >
        {long ? (
          <button
            type="button"
            className={`relative w-full rounded-t-lg px-3 py-2 text-left ${expanded ? "" : "max-h-16 overflow-hidden"}`}
            onClick={() => setExpanded((e) => !e)}
            aria-expanded={expanded}
            title={expanded ? "Click to collapse" : "Click to expand"}
          >
            {!expanded ? (
              <div
                className="pointer-events-none absolute inset-x-0 bottom-0 h-6 bg-gradient-to-t from-[var(--muted)]/90 to-transparent dark:from-[var(--muted)]/80"
                aria-hidden
              />
            ) : null}
            {body}
          </button>
        ) : (
          <div className="px-3 py-2">{body}</div>
        )}
        {long ? (
          <div className="border-t border-[var(--border)]/50 px-3 py-1.5 text-xs text-[var(--muted-foreground)]">
            <button
              type="button"
              className="flex w-full items-center gap-2 text-left text-[var(--muted-foreground)] transition-colors hover:text-[var(--foreground)]"
              onClick={() => setExpanded((e) => !e)}
              aria-expanded={expanded}
            >
              <ChevronRight
                className={`h-3 w-3 shrink-0 transition-transform duration-150 ${expanded ? "rotate-90" : ""}`}
                aria-hidden
              />
              <span>{expanded ? "Show less" : "Show full message"}</span>
            </button>
          </div>
        ) : null}
      </div>
    </div>
  );
}
