import {
  createUIMessageStream,
  createUIMessageStreamResponse,
} from "ai";

const GATEWAY_URL =
  process.env.NEXT_PUBLIC_GATEWAY_URL || "http://localhost:8002";

function isLocalhost(url: string): boolean {
  try {
    const u = new URL(url);
    return u.hostname === "localhost" || u.hostname === "127.0.0.1";
  } catch {
    return false;
  }
}

/**
 * Adapter: receives AI SDK / assistant-ui chat request, calls our Gateway
 * (orchestrator) with stream=true, converts Gateway SSE (thinking, done, error)
 * into AI SDK UI message stream so assistant-ui can render it.
 */
export async function POST(req: Request) {
  if (
    process.env.VERCEL &&
    (!GATEWAY_URL || isLocalhost(GATEWAY_URL))
  ) {
    return new Response(
      JSON.stringify({
        error:
          "NEXT_PUBLIC_GATEWAY_URL is not set for production. Set it in Vercel → Project → Settings → Environment Variables.",
      }),
      { status: 503, headers: { "Content-Type": "application/json" } }
    );
  }

  try {
    const body = (await req.json()) as {
      messages?: { role: string; content?: unknown; parts?: unknown }[];
      text?: string;
      input?: string;
      thread_id?: string;
      user_id?: string;
      bundle_id?: string;
      explore_product_id?: string;
    };

    /** Extract text from message content/parts (AI SDK: string or [{ type: "text", text }]) */
    function extractText(v: unknown): string {
      if (typeof v === "string") return v.trim();
      if (Array.isArray(v))
        return v
          .map((p: { type?: string; text?: string }) =>
            p?.type === "text" && typeof p?.text === "string" ? p.text : ""
          )
          .join("")
          .trim();
      if (v && typeof v === "object" && "text" in v && typeof (v as { text: unknown }).text === "string")
        return ((v as { text: string }).text || "").trim();
      if (v && typeof v === "object" && "parts" in v && Array.isArray((v as { parts: unknown[] }).parts))
        return extractText((v as { parts: unknown[] }).parts);
      return "";
    }

    const messages = body.messages;
    const userMessages = messages?.filter((m) => m.role === "user") ?? [];
    const lastUser = userMessages.pop();
    const fromContent = extractText(lastUser?.content);
    const fromParts = extractText(lastUser?.parts);
    const rawText =
      (typeof body.text === "string" && body.text.trim()) ||
      (typeof body.input === "string" && body.input.trim()) ||
      fromContent ||
      fromParts ||
      userMessages
        .reverse()
        .map((m) => extractText(m.content) || extractText(m.parts))
        .find((t) => t.length > 0) ||
      "";
    const text = rawText || "Find products";

    // Normalize messages so content is always string (orchestrator expects this for recent_conversation)
    const normalizedMessages = messages?.map((m) => ({
      role: m.role,
      content: extractText(m.content) || extractText(m.parts),
    }));

    const payload: Record<string, unknown> = {
      text,
      limit: 20,
      platform: "web",
      stream: true,
    };
    if (normalizedMessages && normalizedMessages.length > 0) payload.messages = normalizedMessages;
    if (body.thread_id) payload.thread_id = body.thread_id;
    if (body.user_id) payload.user_id = body.user_id;
    if (body.bundle_id) payload.bundle_id = body.bundle_id;
    if (body.explore_product_id) payload.explore_product_id = body.explore_product_id;

    const res = await fetch(`${GATEWAY_URL}/api/v1/chat?stream=true&agentic=true`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(95000), // 95s to allow Render cold start (Vercel maxDuration 60 may still apply)
    });

    if (!res.ok) {
      const errText = await res.text();
      return new Response(
        JSON.stringify({ error: errText || `Gateway error: ${res.status}` }),
        { status: res.status, headers: { "Content-Type": "application/json" } }
      );
    }

    if (!res.body) {
      return new Response(
        JSON.stringify({ error: "No response body" }),
        { status: 502, headers: { "Content-Type": "application/json" } }
      );
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    return createUIMessageStreamResponse({
      stream: createUIMessageStream({
        async execute({ writer }) {
          let doneData: Record<string, unknown> | null = null;
          let textStarted = false;

          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const blocks = buffer.split("\n\n");
            buffer = blocks.pop() || "";

            for (const block of blocks) {
              let eventType = "";
              let eventData = "";
              for (const line of block.split("\n")) {
                if (line.startsWith("event: ")) eventType = line.slice(7).trim();
                else if (line.startsWith("data: ")) eventData = line.slice(6);
              }

              if (eventType === "thinking" && eventData) {
                try {
                  const data = JSON.parse(eventData) as { text?: string };
                  writer.write({
                    type: "data-thinking",
                    data: { text: data.text ?? "Thinking..." },
                  });
                } catch {
                  writer.write({
                    type: "data-thinking",
                    data: { text: "Thinking..." },
                  });
                }
              } else if (eventType === "summary_delta" && eventData) {
                try {
                  const data = JSON.parse(eventData) as { delta?: string };
                  const delta = data.delta ?? "";
                  if (!textStarted) {
                    writer.write({ type: "text-start", id: "summary" });
                    textStarted = true;
                  }
                  if (delta) writer.write({ type: "text-delta", id: "summary", delta });
                } catch {
                  // skip malformed delta
                }
              } else if (eventType === "error" && eventData) {
                try {
                  const err = JSON.parse(eventData) as { error?: string };
                  throw new Error(err.error ?? "Stream error");
                } catch (e) {
                  if (e instanceof Error) throw e;
                  throw new Error("Stream error");
                }
              } else if (eventType === "done" && eventData) {
                try {
                  doneData = JSON.parse(eventData) as Record<string, unknown>;
                } catch {
                  // ignore parse error
                }
              }
            }
          }

          if (!doneData) {
            if (!textStarted) {
              writer.write({ type: "text-start", id: "summary" });
              writer.write({ type: "text-delta", id: "summary", delta: "No response from the gateway." });
              writer.write({ type: "text-end", id: "summary" });
            }
            return;
          }

          const summary =
            (doneData.summary as string) ??
            (doneData.message as string) ??
            "I'm here to help. What would you like to explore?";
          const data = doneData.data as Record<string, unknown> | undefined;
          const engagement = data?.engagement as Record<string, unknown> | undefined;
          const productsData = data?.products as { products?: unknown[] } | undefined;
          const productList = productsData?.products ?? [];
          const suggestedOptions = engagement?.suggested_bundle_options as unknown[] | undefined;
          const suggestedCtas = doneData.suggested_ctas as { label?: string; action?: string }[] | undefined;

          if (!textStarted) {
            writer.write({ type: "text-start", id: "summary" });
            writer.write({ type: "text-delta", id: "summary", delta: summary });
          }
          writer.write({ type: "text-end", id: "summary" });

          if (Array.isArray(productList) && productList.length > 0) {
            writer.write({
              type: "data-product_list",
              data: { products: productList },
            });
          }
          if (Array.isArray(suggestedOptions) && suggestedOptions.length > 0) {
            writer.write({
              type: "data-thematic_options",
              data: { options: suggestedOptions },
            });
          }
          if (Array.isArray(suggestedCtas) && suggestedCtas.length > 0) {
            const orderId = (doneData.order_id as string) ?? (doneData.data as Record<string, unknown>)?.order_id as string | undefined;
            writer.write({
              type: "data-engagement_choice",
              data: {
                ctas: suggestedCtas.map((c) => ({
                  ...c,
                  ...(orderId && c.action === "proceed_to_payment" ? { order_id: orderId } : {}),
                })),
                options: suggestedOptions ?? [],
              },
            });
          }
        },
      }),
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
      },
    });
  } catch (err) {
    const msg = err instanceof Error ? err.message : "Chat failed";
    return new Response(
      JSON.stringify({
        error:
          msg.includes("fetch") || msg.includes("ECONNREFUSED") || msg.includes("Failed to fetch")
            ? "Cannot reach gateway. Run Gateway and Discovery first, then start the chat app. Set NEXT_PUBLIC_GATEWAY_URL (e.g. http://localhost:8002)."
            : msg,
      }),
      { status: 500, headers: { "Content-Type": "application/json" } }
    );
  }
}

export const maxDuration = 90;
