"use client";

import { useState } from "react";

type ClassifyResult = {
  classification: string;
  route: string;
  support_escalation_id: string | null;
  id?: string;
};

export default function SupportPage() {
  const [message, setMessage] = useState("");
  const [conversationRef, setConversationRef] = useState("");
  const [result, setResult] = useState<ClassifyResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleClassify = async () => {
    if (!message.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch("/api/support/classify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          conversation_ref: conversationRef.trim() || undefined,
          message_content: message.trim(),
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || "Classification failed");
        return;
      }
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setLoading(false);
    }
  };

  const sampleMessages = [
    { text: "Where is my order?", label: "Routine (AI)" },
    { text: "My order arrived damaged and I want a refund", label: "Human (physical_damage)" },
    { text: "I want to speak to a manager about a wrong charge", label: "Human (dispute)" },
  ];

  return (
    <div className="p-6 max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold mb-1">Support / Hybrid Response</h1>
        <p className="text-sm text-[rgb(var(--color-text-secondary))]">
          Test how customer messages are classified and routed to AI or human. Routine
          queries go to AI; disputes, damage, or complex issues create an escalation.
        </p>
      </div>

      <div className="border border-[rgb(var(--color-border))] rounded-lg p-4 space-y-4">
        <div>
          <label className="block text-sm font-medium mb-2">
            Conversation ref (optional)
          </label>
          <input
            type="text"
            value={conversationRef}
            onChange={(e) => setConversationRef(e.target.value)}
            placeholder="e.g. conv-abc"
            className="w-full rounded border border-[rgb(var(--color-border))] px-3 py-2 bg-[rgb(var(--color-background))] text-[rgb(var(--color-text))]"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-2">
            Customer message
          </label>
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Paste a sample customer message..."
            rows={4}
            className="w-full rounded border border-[rgb(var(--color-border))] px-3 py-2 bg-[rgb(var(--color-background))] text-[rgb(var(--color-text))]"
          />
        </div>
        <button
          onClick={handleClassify}
          disabled={loading || !message.trim()}
          className="px-4 py-2 rounded bg-[rgb(var(--color-primary))] text-white font-medium disabled:opacity-50"
        >
          {loading ? "Classifying…" : "Classify & route"}
        </button>
      </div>

      {error && (
        <div className="p-4 rounded border border-red-500/50 bg-red-500/10 text-red-600 text-sm">
          {error}
        </div>
      )}

      {result && (
        <div className="border border-[rgb(var(--color-border))] rounded-lg p-4 space-y-2">
          <h2 className="font-semibold">Result</h2>
          <div className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
            <span className="text-[rgb(var(--color-text-secondary))]">Classification:</span>
            <span className="font-medium capitalize">{result.classification}</span>
            <span className="text-[rgb(var(--color-text-secondary))]">Route:</span>
            <span className="font-medium capitalize">{result.route}</span>
            {result.support_escalation_id && (
              <>
                <span className="text-[rgb(var(--color-text-secondary))]">Escalation ID:</span>
                <span className="font-mono text-xs">{result.support_escalation_id}</span>
              </>
            )}
          </div>
          <p className="text-xs text-[rgb(var(--color-text-secondary))] mt-2">
            {result.route === "ai"
              ? "Routine query handled by AI."
              : "Escalation created; platform admins can assign and resolve in Escalations."}
          </p>
        </div>
      )}

      <div className="border border-[rgb(var(--color-border))] rounded-lg p-4">
        <h3 className="font-medium mb-2">Sample messages</h3>
        <ul className="space-y-2 text-sm">
          {sampleMessages.map(({ text, label }) => (
            <li key={text}>
              <button
                type="button"
                onClick={() => setMessage(text)}
                className="text-left block w-full p-2 rounded hover:bg-[rgb(var(--color-border))]"
              >
                <span className="text-[rgb(var(--color-text-secondary))] mr-2">{label}</span>
                <span className="font-mono text-xs">{text}</span>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
