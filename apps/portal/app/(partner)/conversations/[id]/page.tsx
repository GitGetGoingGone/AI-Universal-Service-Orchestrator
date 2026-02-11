"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { PartnerGuard, PartnerRequiredMessage } from "@/components/partner-guard";
import { Button } from "@/components/ui/button";

type Message = {
  id: string;
  content: string;
  sender_type: string;
  sender_name: string | null;
  sent_at: string;
};

type Member = {
  id: string;
  email: string;
  display_name: string | null;
  role: string;
};

type Conversation = {
  id: string;
  title: string;
  status: string;
  assigned_to_member_id: string | null;
};

export default function ConversationDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [members, setMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(true);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [assigning, setAssigning] = useState(false);
  const [simulateCustomer, setSimulateCustomer] = useState(false);
  const [partnerRequired, setPartnerRequired] = useState(false);

  const load = () => {
    if (!id) return;
    Promise.all([
      fetch(`/api/partners/conversations/${id}`),
      fetch(`/api/partners/conversations/${id}/messages`),
      fetch("/api/partners/team"),
    ])
      .then(async ([convRes, msgRes, teamRes]) => {
        if (convRes.status === 403 || msgRes.status === 403) {
          setPartnerRequired(true);
          return;
        }
        const conv = await convRes.json();
        const msgData = await msgRes.json();
        const teamData = await teamRes.json();
        if (conv.detail) throw new Error(conv.detail);
        setConversation(conv);
        setMessages(msgData.messages ?? []);
        setMembers(teamData.members ?? []);
      })
      .catch(() => setConversation(null))
      .finally(() => setLoading(false));
  };

  useEffect(() => load(), [id]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !id) return;
    setSending(true);
    try {
      const res = await fetch(`/api/partners/conversations/${id}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          content: input.trim(),
          sender_type: simulateCustomer ? "customer" : "partner",
        }),
      });
      if (res.ok) {
        setInput("");
        load();
      } else {
        const d = await res.json();
        alert(d.detail ?? "Failed");
      }
    } finally {
      setSending(false);
    }
  };

  const handleAssign = async (memberId: string | null) => {
    setAssigning(true);
    try {
      const res = await fetch(`/api/partners/conversations/${id}/assign`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ assigned_to_member_id: memberId }),
      });
      if (res.ok) load();
    } finally {
      setAssigning(false);
    }
  };

  if (loading) return <p className="p-6">Loading…</p>;
  if (partnerRequired) return <PartnerRequiredMessage />;
  if (!conversation) return <p className="p-6">Conversation not found</p>;

  return (
    <PartnerGuard>
      <div className="flex h-[calc(100vh-8rem)] flex-col">
        <header className="flex items-center justify-between p-4 border-b border-[rgb(var(--color-border))]">
          <h1 className="font-semibold">{conversation.title || "Untitled"}</h1>
          <div className="flex items-center gap-2">
            <span className="text-sm text-[rgb(var(--color-text-secondary))]">Assign to:</span>
            <select
              value={conversation.assigned_to_member_id ?? ""}
              onChange={(e) => handleAssign(e.target.value || null)}
              disabled={assigning}
              className="rounded border border-[rgb(var(--color-border))] px-3 py-2 bg-[rgb(var(--color-background))]"
            >
              <option value="">Unassigned</option>
              {members.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.display_name || m.email}
                </option>
              ))}
            </select>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 ? (
            <p className="text-[rgb(var(--color-text-secondary))] text-sm">No messages yet</p>
          ) : (
            messages.map((m) => (
              <div
                key={m.id}
                className={`flex ${m.sender_type === "partner" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[80%] rounded-lg px-4 py-2 ${
                    m.sender_type === "partner"
                      ? "bg-[rgb(var(--color-primary))] text-[rgb(var(--color-primary-foreground))]"
                      : m.sender_type === "ai"
                        ? "bg-blue-100 text-blue-900"
                        : "bg-[rgb(var(--color-surface))] border border-[rgb(var(--color-border))]"
                  }`}
                >
                  <p className="text-xs opacity-80 mb-1">
                    {m.sender_name || m.sender_type} · {new Date(m.sent_at).toLocaleString()}
                  </p>
                  <p className="text-sm whitespace-pre-wrap">{m.content}</p>
                </div>
              </div>
            ))
          )}
        </div>

        <form onSubmit={handleSend} className="p-4 border-t border-[rgb(var(--color-border))] flex gap-2 flex-wrap items-center">
          <label className="flex items-center gap-2 text-sm text-[rgb(var(--color-text-secondary))]">
            <input
              type="checkbox"
              checked={simulateCustomer}
              onChange={(e) => setSimulateCustomer(e.target.checked)}
              className="rounded border-[rgb(var(--color-border))]"
            />
            Simulate customer (triggers AI)
          </label>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type a message..."
            className="flex-1 rounded border border-[rgb(var(--color-border))] px-4 py-2 bg-[rgb(var(--color-background))]"
          />
          <Button type="submit" disabled={sending || !input.trim()}>
            Send
          </Button>
        </form>
      </div>
    </PartnerGuard>
  );
}
