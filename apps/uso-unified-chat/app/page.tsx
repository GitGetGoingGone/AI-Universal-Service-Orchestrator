"use client";

import { useState } from "react";

type Provider = "chatgpt" | "gemini";

export default function ChatPage() {
  const [provider, setProvider] = useState<Provider>("chatgpt");
  const [messages, setMessages] = useState<{ role: string; content: string }[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setLoading(true);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ provider, messages: [...messages, { role: "user", content: userMessage }] }),
      });

      type ChatResponse = {
        data?: {
          products?: { products?: Array<{ name?: string; price?: number }>; count?: number };
          text?: string;
          error?: string;
        };
        summary?: string;
        message?: string;
        error?: string;
      };
      let data: ChatResponse;
      try {
        data = (await res.json()) as ChatResponse;
      } catch {
        throw new Error(res.ok ? "Invalid response" : `HTTP ${res.status}`);
      }
      if (!res.ok) {
        const errMsg = data?.error || `HTTP ${res.status}`;
        throw new Error(errMsg);
      }
      const productList = data.data?.products?.products ?? [];
      const assistantContent =
        data.summary ??
        (productList.length > 0
          ? `Found ${productList.length} products:\n${productList
              .slice(0, 5)
              .map((p) => `- ${p.name} ($${p.price})`)
              .join("\n")}`
          : data.data?.text ?? data.message ?? JSON.stringify(data));

      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: assistantContent },
      ]);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Error: ${msg}` },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ maxWidth: 600, margin: "0 auto", padding: 24 }}>
      <h1>USO Unified Chat</h1>

      <div style={{ marginBottom: 16 }}>
        <label>Provider: </label>
        <select
          value={provider}
          onChange={(e) => setProvider(e.target.value as Provider)}
          disabled={loading}
        >
          <option value="chatgpt">ChatGPT</option>
          <option value="gemini">Gemini</option>
        </select>
        <span style={{ marginLeft: 8, color: "#666" }}>
          (Backend: Orchestrator)
        </span>
      </div>

      <div
        style={{
          border: "1px solid #ccc",
          borderRadius: 8,
          minHeight: 300,
          padding: 16,
          marginBottom: 16,
          background: "#fafafa",
        }}
      >
        {messages.length === 0 && (
          <p style={{ color: "#666" }}>
            Try: &quot;Find me flowers&quot; or &quot;I want chocolates&quot;
          </p>
        )}
        {messages.map((m, i) => (
          <div
            key={i}
            style={{
              marginBottom: 12,
              padding: 8,
              background: m.role === "user" ? "#e3f2fd" : "#fff",
              borderRadius: 4,
            }}
          >
            <strong>{m.role}:</strong> {m.content}
          </div>
        ))}
        {loading && <p style={{ color: "#666" }}>Loading...</p>}
      </div>

      <form onSubmit={handleSubmit}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a message..."
          disabled={loading}
          style={{
            width: "100%",
            padding: 12,
            borderRadius: 8,
            border: "1px solid #ccc",
          }}
        />
        <button
          type="submit"
          disabled={loading}
          style={{
            marginTop: 8,
            padding: "12px 24px",
            background: "#1976d2",
            color: "white",
            border: "none",
            borderRadius: 8,
          }}
        >
          Send
        </button>
      </form>
    </div>
  );
}
