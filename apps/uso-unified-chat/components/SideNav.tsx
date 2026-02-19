"use client";

import Link from "next/link";

export type ThreadItem = {
  id: string;
  title: string;
  updated_at: string;
  has_completed_order?: boolean;
};

type SideNavProps = {
  collapsed: boolean;
  onToggle: () => void;
  /** When provided, show thread list and chat actions */
  threadId?: string | null;
  threads?: ThreadItem[];
  onNewChat?: () => void;
  onSelectThread?: (id: string | null) => void;
  onDeleteThread?: (id: string) => void;
  hasUserOrAnonymous?: boolean;
  anonymousId?: string | null;
};

export function SideNav({
  collapsed,
  onToggle,
  threadId,
  threads = [],
  onNewChat,
  onSelectThread,
  onDeleteThread,
  hasUserOrAnonymous,
}: SideNavProps) {
  const showThreadList = threadId !== undefined && onNewChat && onSelectThread;

  return (
    <aside
      className={`flex-shrink-0 flex flex-col border-r border-[var(--border)] bg-[var(--card)] text-[var(--card-foreground)] transition-[width] duration-200 ${
        collapsed ? "w-14" : "w-64"
      }`}
    >
      <div className={`flex h-14 items-center border-b border-[var(--border)] ${collapsed ? "justify-center px-0" : "justify-between px-3"}`}>
        {!collapsed && (
          <Link href="/" className="font-semibold text-[var(--foreground)] truncate">
            Chat
          </Link>
        )}
        <button
          type="button"
          onClick={onToggle}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          className="rounded p-2 text-[var(--muted)] transition-colors hover:bg-[var(--border)] hover:text-[var(--foreground)]"
        >
          <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            {collapsed ? (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            ) : (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            )}
          </svg>
        </button>
      </div>

      {/* When collapsed: icon-only nav (Chat, Settings) so we don't need a duplicate menu in main content */}
      {collapsed && (
        <nav className="flex flex-col items-center gap-1 py-2">
          <Link
            href="/"
            aria-label="Chat"
            className="rounded p-2.5 text-[var(--muted)] transition-colors hover:bg-[var(--border)] hover:text-[var(--foreground)]"
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
          </Link>
          <Link
            href="/settings"
            aria-label="Settings"
            className="rounded p-2.5 text-[var(--muted)] transition-colors hover:bg-[var(--border)] hover:text-[var(--foreground)]"
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </Link>
        </nav>
      )}

      {showThreadList && hasUserOrAnonymous && !collapsed && (
        <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
          <div className="p-2">
            <button
              type="button"
              onClick={onNewChat}
              className="flex w-full items-center gap-2 rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm font-medium text-[var(--foreground)] hover:border-[var(--primary-color)]/50 hover:bg-[var(--primary-color)]/10"
            >
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              New chat
            </button>
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto px-2 pb-4">
            <p className="mb-2 px-2 text-xs font-medium uppercase tracking-wider text-[var(--muted)]">
              Conversations
            </p>
            <ul className="space-y-0.5">
              {threads.map((t) => (
                <li key={t.id}>
                  <div className="group flex items-center gap-1 rounded-lg hover:bg-[var(--border)]/50">
                    <button
                      type="button"
                      onClick={() => onSelectThread?.(t.id)}
                      className={`min-w-0 flex-1 truncate px-3 py-2 text-left text-sm ${
                        threadId === t.id
                          ? "font-medium text-[var(--primary-color)]"
                          : "text-[var(--foreground)]"
                      }`}
                    >
                      {t.title.length > 28 ? t.title.slice(0, 25) + "…" : t.title || "Chat"}
                    </button>
                    {onDeleteThread && (
                      <button
                        type="button"
                        onClick={() => onDeleteThread(t.id)}
                        aria-label="Delete conversation"
                        className="rounded p-1.5 text-[var(--muted)] opacity-0 transition-opacity hover:bg-red-500/20 hover:text-red-500 group-hover:opacity-100"
                      >
                        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                          />
                        </svg>
                      </button>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {!showThreadList && !collapsed && (
        <nav className="flex flex-col gap-1 p-2">
          <Link
            href="/"
            className="rounded-lg px-3 py-2 text-sm text-[var(--foreground)] hover:bg-[var(--border)]/50"
          >
            Chat
          </Link>
          <Link
            href="/settings"
            className="rounded-lg px-3 py-2 text-sm text-[var(--foreground)] hover:bg-[var(--border)]/50"
          >
            Settings
          </Link>
        </nav>
      )}
    </aside>
  );
}
