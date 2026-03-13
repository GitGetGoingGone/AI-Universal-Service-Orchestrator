"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname, useSearchParams } from "next/navigation";
import { PartnerGuard, PartnerRequiredMessage } from "@/components/partner-guard";
import { Button } from "@/components/ui/button";
import { MessageCircle, Plus } from "lucide-react";

type Conversation = {
  id: string;
  title: string;
  status: string;
  assigned_to_member_id: string | null;
  created_at: string;
  updated_at: string;
};

type LastMessages = Record<string, { content: string; sent_at: string }>;

const FILTERS = [
  { value: "all" as const, label: "All" },
  { value: "mine" as const, label: "Mine" },
  { value: "unassigned" as const, label: "Unassigned" },
];

export function ConversationSidebar() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const urlFilter = searchParams.get("filter");
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [lastMessages, setLastMessages] = useState<LastMessages>({});
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"all" | "mine" | "unassigned">(
    urlFilter === "unassigned" ? "unassigned" : urlFilter === "mine" ? "mine" : "all"
  );
  const [myMemberId, setMyMemberId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [partnerRequired, setPartnerRequired] = useState(false);

  useEffect(() => {
    const f = urlFilter === "unassigned" ? "unassigned" : urlFilter === "mine" ? "mine" : "all";
    setFilter(f);
  }, [urlFilter]);

  useEffect(() => {
    fetch("/api/partners/current-member")
      .then((r) => r.json())
      .then((d) => setMyMemberId(d.memberId ?? null))
      .catch(() => setMyMemberId(null));
  }, []);

  useEffect(() => {
    setLoading(true);
    setPartnerRequired(false);
    const params = new URLSearchParams();
    if (filter !== "all") params.set("filter", filter);
    if (filter === "mine" && myMemberId) params.set("my_member_id", myMemberId);
    fetch(`/api/partners/conversations?${params}`)
      .then((r) => {
        if (r.status === 403) {
          setPartnerRequired(true);
          return { conversations: [], lastMessages: {} };
        }
        return r.json();
      })
      .then((d) => {
        setConversations(d.conversations ?? []);
        setLastMessages(d.lastMessages ?? {});
      })
      .catch(() => setConversations([]))
      .finally(() => setLoading(false));
  }, [filter, myMemberId]);

  const handleNew = async () => {
    setCreating(true);
    try {
      const res = await fetch("/api/partners/conversations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: "New conversation" }),
      });
      const data = await res.json();
      if (res.ok) {
        router.push(`/conversations/${data.id}`);
      } else {
        setCreating(false);
        return;
      }
    } catch {
      // keep creating false in finally
    } finally {
      setCreating(false);
    }
  };

  const setFilterAndUrl = (f: "all" | "mine" | "unassigned") => {
    setFilter(f);
    const isListPage = pathname === "/conversations" || pathname === "/conversations/";
    if (isListPage) {
      const params = new URLSearchParams(searchParams);
      if (f === "all") params.delete("filter");
      else params.set("filter", f);
      router.replace(`/conversations?${params.toString()}`, { scroll: false });
    }
  };

  const activeId = pathname?.startsWith("/conversations/") ? pathname.split("/").pop() : null;

  if (partnerRequired) return <PartnerRequiredMessage />;

  return (
    <PartnerGuard>
      <aside
        className="w-64 sm:w-72 shrink-0 border-r border-[rgb(var(--color-border))] flex flex-col bg-[rgb(var(--color-surface))] min-h-0"
        aria-label="Conversations list"
      >
        <div className="p-4 border-b border-[rgb(var(--color-border))] shrink-0">
          <Button
            onClick={handleNew}
            disabled={creating}
            className="w-full gap-2"
            aria-label={creating ? "Creating conversation" : "New conversation"}
          >
            <Plus className="size-4" aria-hidden />
            {creating ? "Creating…" : "New conversation"}
          </Button>
        </div>
        <div className="flex gap-1 p-2 shrink-0">
          {FILTERS.map((f) => (
            <button
              key={f.value}
              onClick={() => setFilterAndUrl(f.value)}
              className={`flex-1 px-2 py-1.5 rounded-lg text-xs font-medium capitalize transition-colors ${
                filter === f.value
                  ? "bg-[rgb(var(--color-primary))] text-[rgb(var(--color-primary-foreground))]"
                  : "bg-[rgb(var(--color-background))] text-[rgb(var(--color-text-secondary))] hover:bg-[rgb(var(--color-border))]/50"
              }`}
              aria-pressed={filter === f.value}
              aria-label={`Filter: ${f.label}`}
            >
              {f.label}
            </button>
          ))}
        </div>
        <nav className="flex-1 overflow-y-auto p-2 min-h-0" aria-label="Conversation threads">
          {loading ? (
            <div className="p-4 space-y-2" aria-busy="true">
              <div className="h-14 rounded-lg bg-[rgb(var(--color-border))]/30 animate-pulse" />
              <div className="h-14 rounded-lg bg-[rgb(var(--color-border))]/30 animate-pulse" />
              <div className="h-14 rounded-lg bg-[rgb(var(--color-border))]/30 animate-pulse" />
            </div>
          ) : conversations.length === 0 ? (
            <div className="p-4 text-center">
              <MessageCircle className="size-10 mx-auto text-[rgb(var(--color-text-secondary))]/50 mb-2" aria-hidden />
              <p className="text-sm text-[rgb(var(--color-text-secondary))]">No conversations yet</p>
              <p className="text-xs text-[rgb(var(--color-text-secondary))]/80 mt-1">
                Create one above or they’ll appear when customers message.
              </p>
            </div>
          ) : (
            <ul className="space-y-1" role="list">
              {conversations.map((c) => (
                <li key={c.id}>
                  <button
                    type="button"
                    onClick={() => router.push(`/conversations/${c.id}`)}
                    className={`w-full text-left p-3 rounded-lg border transition-colors focus:outline-none focus:ring-2 focus:ring-[rgb(var(--color-primary))] focus:ring-offset-2 ${
                      activeId === c.id
                        ? "bg-[rgb(var(--color-primary))] text-[rgb(var(--color-primary-foreground))] border-[rgb(var(--color-primary))]"
                        : "hover:bg-[rgb(var(--color-background))] border-transparent hover:border-[rgb(var(--color-border))]"
                    }`}
                    aria-current={activeId === c.id ? "true" : undefined}
                  >
                    <p className="font-medium text-sm truncate">{c.title || "Untitled"}</p>
                    <p className="text-xs opacity-80 truncate mt-0.5">
                      {lastMessages[c.id]?.content?.slice(0, 50) || "No messages"}
                    </p>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </nav>
      </aside>
    </PartnerGuard>
  );
}
