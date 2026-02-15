"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ConnectWhatsApp } from "@/components/ConnectWhatsApp";

export type MyStuff = {
  favorites: Array<{ id: string; item_type: string; item_id: string; item_name: string | null; created_at: string }>;
  standing_intents: Array<{ id: string; intent_description: string; status: string; created_at: string }>;
};

export type SideNavProps = {
  threadId?: string | null;
  threads?: Array<{ id: string; title: string; updated_at: string }>;
  onNewChat?: () => void;
  onSelectThread?: (id: string | null) => void;
  hasUserOrAnonymous?: boolean;
  anonymousId?: string | null;
};

export function SideNav({
  threadId = null,
  threads = [],
  onNewChat,
  onSelectThread,
  hasUserOrAnonymous = false,
  anonymousId,
}: SideNavProps) {
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

      {/* My Stuff */}
      <div className="px-2">
        <button
          type="button"
          onClick={() => setMyStuffOpen((o) => !o)}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-[var(--card-foreground)] transition-colors hover:bg-[var(--background)]"
        >
          <span className="text-base" aria-hidden>⭐</span>
          My Stuff
          {hasMyStuff && (
            <span className="ml-auto rounded-full bg-[var(--primary-color)]/20 px-1.5 py-0.5 text-xs text-[var(--primary-color)]">
              {myStuff.favorites.length + myStuff.standing_intents.length}
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

      {/* Thread list - always visible when user has identity */}
      {hasUserOrAnonymous && (
        <div className="flex-1 overflow-y-auto px-2">
          <div className="space-y-0.5 py-2">
            {threads.length === 0 ? (
              <p className="px-3 py-2 text-xs text-[var(--muted)]">No conversations yet</p>
            ) : (
              threads.map((t) => (
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
              ))
            )}
          </div>
        </div>
      )}

      {/* Bottom: Connect, Settings (Settings last) - fixed at bottom left */}
      <div className="mt-auto flex-shrink-0 flex flex-col gap-1 border-t border-[var(--border)] p-3">
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
