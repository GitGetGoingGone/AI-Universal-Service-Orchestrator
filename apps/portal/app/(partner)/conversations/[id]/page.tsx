"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { PartnerGuard, PartnerRequiredMessage } from "@/components/partner-guard";
import { Button } from "@/components/ui/button";
import { ChevronLeft } from "lucide-react";

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

type Feedback = { type: "success" | "error"; text: string } | null;

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
  const [feedback, setFeedback] = useState<Feedback>(null);

  useEffect(() => {
    if (!feedback) return;
    const t = setTimeout(() => setFeedback(null), 5000);
    return () => clearTimeout(t);
  }, [feedback]);

  const showFeedback = (type: "success" | "error", text: string) => {
    setFeedback({ type, text });
  };

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
    setFeedback(null);
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
        showFeedback("success", "Message sent.");
      } else {
        const d = await res.json();
        showFeedback("error", d.detail ?? "Failed to send.");
      }
    } catch {
      showFeedback("error", "Failed to send.");
    } finally {
      setSending(false);
    }
  };

  const handleAssign = async (memberId: string | null) => {
    setAssigning(true);
    setFeedback(null);
    try {
      const res = await fetch(`/api/partners/conversations/${id}/assign`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ assigned_to_member_id: memberId }),
      });
      if (res.ok) {
        load();
        showFeedback("success", "Assignment updated.");
      } else {
        const d = await res.json();
        showFeedback("error", d.detail ?? "Failed to assign.");
      }
    } catch {
      showFeedback("error", "Failed to assign.");
    } finally {
      setAssigning(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col h-full min-h-0 animate-pulse">
        <div className="h-16 border-b border-[rgb(var(--color-border))] bg-[rgb(var(--color-surface))]/50" />
        <div className="flex-1 p-4 space-y-4">
          <div className="h-16 rounded-lg bg-[rgb(var(--color-border))]/30 w-3/4" />
          <div className="h-16 rounded-lg bg-[rgb(var(--color-border))]/30 w-2/3 ml-auto" />
          <div className="h-16 rounded-lg bg-[rgb(var(--color-border))]/30 w-4/5" />
        </div>
        <div className="h-20 border-t border-[rgb(var(--color-border))]" />
      </div>
    );
  }
  if (partnerRequired) return <PartnerRequiredMessage />;
  if (!conversation) {
    return (
      <div className="flex flex-col items-center justify-center p-8 min-h-0">
        <p className="text-[rgb(var(--color-text-secondary))] mb-4">Conversation not found.</p>
        <Link
          href="/conversations"
          className="inline-flex items-center gap-2 text-[rgb(var(--color-primary))] hover:underline"
        >
          <ChevronLeft className="size-4" /> Back to conversations
        </Link>
      </div>
    );
  }

  return (
    <PartnerGuard>
      <div className="flex flex-col h-full min-h-0">
        <header className="flex items-center justify-between gap-4 p-4 border-b border-[rgb(var(--color-border))] shrink-0 flex-wrap">
          <div className="flex items-center gap-2 min-w-0">
            <Link
              href="/conversations"
              className="shrink-0 rounded p-1 text-[rgb(var(--color-text-secondary))] hover:bg-[rgb(var(--color-border))]/50 hover:text-[rgb(var(--color-text))] focus:outline-none focus:ring-2 focus:ring-[rgb(var(--color-primary))]"
              aria-label="Back to conversations"
            >
              <ChevronLeft className="size-4" />
            </Link>
            <h1 className="font-semibold truncate" id="conversation-title">
              {conversation.title || "Untitled"}
            </h1>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm text-[rgb(var(--color-text-secondary))]" id="assign-label">
              Assign to:
            </span>
            <select
              value={conversation.assigned_to_member_id ?? ""}
              onChange={(e) => handleAssign(e.target.value || null)}
              disabled={assigning}
              aria-labelledby="assign-label"
              className="rounded-lg border border-[rgb(var(--color-border))] px-3 py-2 bg-[rgb(var(--color-background))] text-sm min-w-[140px]"
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

        {feedback && (
          <div
            role="status"
            className={`mx-4 mt-2 px-4 py-2 rounded-lg text-sm ${
              feedback.type === "success"
                ? "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-200"
                : "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-200"
            }`}
          >
            {feedback.text}
          </div>
        )}

        <div
          className="flex-1 overflow-y-auto p-4 space-y-4 min-h-0"
          aria-label="Message thread"
        >
          {messages.length === 0 ? (
            <p className="text-[rgb(var(--color-text-secondary))] text-sm">No messages yet. Send one below.</p>
          ) : (
            <ul className="space-y-4" role="list">
              {messages.map((m) => (
                <li
                  key={m.id}
                  className={`flex ${m.sender_type === "partner" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[85%] rounded-xl px-4 py-2.5 ${
                      m.sender_type === "partner"
                        ? "bg-[rgb(var(--color-primary))] text-[rgb(var(--color-primary-foreground))]"
                        : m.sender_type === "ai"
                          ? "bg-blue-100 text-blue-900 dark:bg-blue-900/40 dark:text-blue-100"
                          : "bg-[rgb(var(--color-surface))] border border-[rgb(var(--color-border))]"
                    }`}
                  >
                    <p className="text-xs opacity-80 mb-1">
                      {m.sender_name || m.sender_type} · {new Date(m.sent_at).toLocaleString()}
                    </p>
                    <p className="text-sm whitespace-pre-wrap">{m.content}</p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        <form
          onSubmit={handleSend}
          className="p-4 border-t border-[rgb(var(--color-border))] shrink-0 flex gap-2 flex-wrap items-center bg-[rgb(var(--color-surface))]/50"
        >
          <label className="flex items-center gap-2 text-sm text-[rgb(var(--color-text-secondary))] cursor-pointer">
            <input
              type="checkbox"
              checked={simulateCustomer}
              onChange={(e) => setSimulateCustomer(e.target.checked)}
              className="rounded border-[rgb(var(--color-border))] text-[rgb(var(--color-primary))] focus:ring-[rgb(var(--color-primary))]"
            />
            Simulate customer (triggers AI)
          </label>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type a message..."
            className="flex-1 min-w-[200px] rounded-lg border border-[rgb(var(--color-border))] px-4 py-2 bg-[rgb(var(--color-background))] text-[rgb(var(--color-text))] placeholder:text-[rgb(var(--color-text-secondary))]/70 focus:outline-none focus:ring-2 focus:ring-[rgb(var(--color-primary))] focus:border-transparent"
            aria-label="Message content"
          />
          <Button type="submit" disabled={sending || !input.trim()}>
            {sending ? "Sending…" : "Send"}
          </Button>
        </form>
      </div>
    </PartnerGuard>
  );
}
