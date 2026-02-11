"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { PartnerGuard, PartnerRequiredMessage } from "@/components/partner-guard";
import { Button } from "@/components/ui/button";

type Conversation = {
  id: string;
  title: string;
  status: string;
  assigned_to_member_id: string | null;
  created_at: string;
  updated_at: string;
};

type LastMessages = Record<string, { content: string; sent_at: string }>;

export function ConversationSidebar() {
  const router = useRouter();
  const pathname = usePathname();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [lastMessages, setLastMessages] = useState<LastMessages>({});
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"all" | "mine" | "unassigned">("all");
  const [myMemberId, setMyMemberId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [partnerRequired, setPartnerRequired] = useState(false);

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
        alert(data.detail ?? "Failed");
      }
    } finally {
      setCreating(false);
    }
  };

  const activeId = pathname?.startsWith("/conversations/") ? pathname.split("/").pop() : null;

  if (partnerRequired) return <PartnerRequiredMessage />;

  return (
    <PartnerGuard>
      <aside className="w-64 shrink-0 border-r border-[rgb(var(--color-border))] flex flex-col bg-[rgb(var(--color-background))]">
        <div className="p-4 border-b border-[rgb(var(--color-border))]">
          <Button onClick={handleNew} disabled={creating} className="w-full">
            {creating ? "Creating…" : "+ New conversation"}
          </Button>
        </div>
        <div className="flex gap-1 p-2">
          {(["all", "mine", "unassigned"] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`flex-1 px-2 py-1 rounded text-xs capitalize ${
                filter === f
                  ? "bg-[rgb(var(--color-primary))] text-[rgb(var(--color-primary-foreground))]"
                  : "bg-[rgb(var(--color-surface))]"
              }`}
            >
              {f}
            </button>
          ))}
        </div>
        <nav className="flex-1 overflow-y-auto p-2">
          {loading ? (
            <p className="text-sm text-[rgb(var(--color-text-secondary))] p-4">Loading…</p>
          ) : conversations.length === 0 ? (
            <p className="text-sm text-[rgb(var(--color-text-secondary))] p-4">No conversations</p>
          ) : (
            <ul className="space-y-1">
              {conversations.map((c) => (
                <li key={c.id}>
                  <button
                    onClick={() => router.push(`/conversations/${c.id}`)}
                    className={`w-full text-left p-3 rounded-lg border transition ${
                      activeId === c.id
                        ? "bg-[rgb(var(--color-primary))] text-[rgb(var(--color-primary-foreground))] border-[rgb(var(--color-primary))]"
                        : "hover:bg-[rgb(var(--color-surface))] border-transparent hover:border-[rgb(var(--color-border))]"
                    }`}
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
