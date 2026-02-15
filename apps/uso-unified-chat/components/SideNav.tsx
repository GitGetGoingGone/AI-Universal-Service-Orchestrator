"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ConnectWhatsApp } from "@/components/ConnectWhatsApp";

export type SideNavProps = {
  threadId?: string | null;
  threads?: Array<{ id: string; title: string; updated_at: string }>;
  onNewChat?: () => void;
  onSelectThread?: (id: string | null) => void;
  hasUserOrAnonymous?: boolean;
};

export function SideNav({
  threadId = null,
  threads = [],
  onNewChat,
  onSelectThread,
  hasUserOrAnonymous = false,
}: SideNavProps) {
  const pathname = usePathname();
  const isSettings = pathname === "/settings";

  return (
    <aside className="flex w-64 flex-shrink-0 flex-col border-r border-[var(--border)] bg-[var(--card)]">
      {/* New chat */}
      <div className="p-3">
        {onNewChat ? (
          <button
            type="button"
            onClick={onNewChat}
            className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-[var(--card-foreground)] transition-colors hover:bg-[var(--background)]"
          >
            <span className="text-lg">+</span>
            New chat
          </button>
        ) : (
          <Link
            href="/"
            className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-[var(--card-foreground)] transition-colors hover:bg-[var(--background)]"
          >
            <span className="text-lg">+</span>
            New chat
          </Link>
        )}
      </div>

      {/* Thread list */}
      {hasUserOrAnonymous && threads.length > 0 && (
        <div className="flex-1 overflow-y-auto px-2">
          <div className="space-y-0.5 py-2">
            {threads.map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => onSelectThread?.(t.id)}
                className={`w-full rounded-lg px-3 py-2 text-left text-sm truncate transition-colors ${
                  threadId === t.id
                    ? "bg-[var(--primary-color)]/20 text-[var(--primary-color)]"
                    : "text-[var(--muted)] hover:bg-[var(--background)] hover:text-[var(--card-foreground)]"
                }`}
                title={t.title}
              >
                {t.title.length > 24 ? t.title.slice(0, 21) + "…" : t.title}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Bottom: Connect, Settings */}
      <div className="flex flex-col gap-1 border-t border-[var(--border)] p-3">
        <ConnectWhatsApp />
        <Link
          href="/settings"
          className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors hover:bg-[var(--background)] ${
            isSettings
              ? "bg-[var(--primary-color)]/20 text-[var(--primary-color)]"
              : "text-[var(--muted)] hover:text-[var(--card-foreground)]"
          }`}
        >
          <span className="text-base">⚙️</span>
          Settings
        </Link>
      </div>
    </aside>
  );
}
