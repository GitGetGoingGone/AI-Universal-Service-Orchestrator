"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { AuthButtons } from "@/components/AuthWrapper";
import { ConnectWhatsApp } from "@/components/ConnectWhatsApp";

export type ThreadItem = {
  id: string;
  title: string;
  updated_at: string;
  has_completed_order?: boolean;
};

export type MyStuff = {
  favorites: Array<{ id: string; item_type: string; item_id: string; item_name: string | null; created_at: string }>;
  standing_intents: Array<{ id: string; intent_description: string; status: string; created_at: string }>;
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
  anonymousId,
}: SideNavProps) {
  const showThreadList = threadId !== undefined && onNewChat && onSelectThread;
  const pathname = usePathname();
  const isSettings = pathname === "/settings";

  const [myStuff, setMyStuff] = useState<MyStuff | null>(null);
  const [myStuffOpen, setMyStuffOpen] = useState(false);

  const fetchMyStuff = useCallback(() => {
    const params = anonymousId ? `?anonymous_id=${encodeURIComponent(anonymousId)}` : "";
    fetch(`/api/my-stuff${params}`)
      .then((r) => r.json())
      .then((d) => setMyStuff({ favorites: d.favorites ?? [], standing_intents: d.standing_intents ?? [] }))
      .catch(() => setMyStuff({ favorites: [], standing_intents: [] }));
  }, [anonymousId]);

  useEffect(() => {
    fetchMyStuff();
  }, [fetchMyStuff]);

  useEffect(() => {
    const onRefresh = () => fetchMyStuff();
    window.addEventListener("my-stuff-refresh", onRefresh);
    return () => window.removeEventListener("my-stuff-refresh", onRefresh);
  }, [fetchMyStuff]);

  const hasMyStuff = myStuff && (myStuff.favorites.length > 0 || myStuff.standing_intents.length > 0);

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
                    {onDeleteThread && !t.has_completed_order && (
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

      {/* My Stuff (favorites + standing intents) - matches d002d5c^ SideNav */}
      {!collapsed && (
        <div className="px-2">
          <button
            type="button"
            onClick={() => setMyStuffOpen((o) => !o)}
            className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-[var(--card-foreground)] transition-colors hover:bg-[var(--border)]/50"
          >
            <span className="text-base" aria-hidden>⭐</span>
            My Stuff
            {hasMyStuff && (
              <span className="ml-auto rounded-full bg-[var(--primary-color)]/20 px-1.5 py-0.5 text-xs text-[var(--primary-color)]">
                {myStuff!.favorites.length + myStuff!.standing_intents.length}
              </span>
            )}
          </button>
          {myStuffOpen && (
            <div className="mt-1 space-y-1 pl-2">
              {myStuff?.standing_intents && myStuff.standing_intents.length > 0 && (
                <div className="py-1">
                  <p className="mb-1 text-xs font-medium uppercase tracking-wider text-[var(--muted)]">
                    Standing Instructions
                  </p>
                  {myStuff.standing_intents.map((si) => (
                    <div
                      key={si.id}
                      className="rounded-lg px-2 py-1.5 text-xs text-[var(--card-foreground)]"
                      title={si.intent_description}
                    >
                      {si.intent_description.length > 28
                        ? si.intent_description.slice(0, 25) + "…"
                        : si.intent_description}
                    </div>
                  ))}
                </div>
              )}
              {myStuff?.favorites && myStuff.favorites.length > 0 && (
                <div className="py-1">
                  <p className="mb-1 text-xs font-medium uppercase tracking-wider text-[var(--muted)]">
                    Favorites
                  </p>
                  {myStuff.favorites.map((f) => (
                    <div
                      key={f.id}
                      className="rounded-lg px-2 py-1.5 text-xs text-[var(--card-foreground)]"
                      title={f.item_name || f.item_id}
                    >
                      {f.item_name && f.item_name.length > 28
                        ? f.item_name.slice(0, 25) + "…"
                        : f.item_name || f.item_id}
                    </div>
                  ))}
                </div>
              )}
              {myStuff && myStuff.favorites.length === 0 && myStuff.standing_intents.length === 0 && (
                <p className="py-2 text-xs text-[var(--muted)]">No favorites or standing instructions yet.</p>
              )}
            </div>
          )}
        </div>
      )}

      {/* Bottom: Connect WhatsApp, Sign in/out, Settings - matches d002d5c^ SideNav */}
      {!collapsed && (
        <div className="mt-auto flex-shrink-0 flex flex-col gap-1 border-t border-[var(--border)] p-2">
          <div className="px-1">
            <ConnectWhatsApp />
          </div>
          <div className="px-1">
            <AuthButtons />
          </div>
          <Link
            href="/settings"
            className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors hover:bg-[var(--border)]/50 ${
              isSettings
                ? "bg-[var(--primary-color)]/20 text-[var(--primary-color)]"
                : "text-[var(--card-foreground)]"
            }`}
          >
            <span className="text-base" aria-hidden>⚙️</span>
            Settings
          </Link>
        </div>
      )}
    </aside>
  );
}
