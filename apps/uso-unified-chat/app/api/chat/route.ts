import { NextResponse } from "next/server";
import { getSupabase } from "@/lib/supabase";

const ORCHESTRATOR_URL =
  process.env.ORCHESTRATOR_URL || "http://localhost:8002";

function isLocalhost(url: string): boolean {
  try {
    const u = new URL(url);
    return u.hostname === "localhost" || u.hostname === "127.0.0.1";
  } catch {
    return false;
  }
}

/** Derive a human-friendly conversation title from the orchestrator response. */
function deriveThreadTitle(data: Record<string, unknown>, fallback: string): string {
  const d = data.data as Record<string, unknown> | undefined;
  const intent = d?.intent as Record<string, unknown> | undefined;
  const searchQuery = (intent?.search_query as string) || "";
  const intentType = (intent?.intent_type as string) || "";

  // For composite discovery (date night, gifts, etc.), use "Planning [query]"
  if (intentType === "discover_composite" && searchQuery) {
    const capped = searchQuery.slice(0, 40);
    return `Planning ${capped.charAt(0).toUpperCase() + capped.slice(1)}`;
  }

  // For browse/explore, use the query
  if (searchQuery && searchQuery.length <= 50) {
    return searchQuery.charAt(0).toUpperCase() + searchQuery.slice(1);
  }

  // Fallback: first user message, truncated
  return fallback.slice(0, 50) || "New chat";
}

export async function POST(req: Request) {
  // In production (Vercel), localhost will not work
  if (
    process.env.VERCEL &&
    (!ORCHESTRATOR_URL || isLocalhost(ORCHESTRATOR_URL))
  ) {
    return NextResponse.json(
      {
        error:
          "ORCHESTRATOR_URL is not configured. Set it in Vercel → Project → Settings → Environment Variables (e.g. https://uso-orchestrator.onrender.com)",
      },
      { status: 503 }
    );
  }

  try {
    const body = await req.json();
    const {
      messages,
      partner_id,
      user_id,
      thread_id,
      anonymous_id,
      bundle_id,
      order_id,
      stream: streamRequested,
      debug: debugRequested,
    } = body as {
      messages?: { role: string; content: string }[];
      partner_id?: string;
      user_id?: string;
      thread_id?: string;
      anonymous_id?: string;
      bundle_id?: string;
      order_id?: string;
      stream?: boolean;
      debug?: boolean;
    };

    const lastUserMessage =
      messages
        ?.filter((m) => m.role === "user")
        .pop()?.content || "Find products";

    const supabase = getSupabase();
    let resolvedThreadId = thread_id;
    let isNewThread = false;

    if (supabase && (thread_id || anonymous_id || user_id)) {
      if (thread_id) {
        const { data: thread } = await supabase
          .from("chat_threads")
          .select("id, anonymous_id, user_id")
          .eq("id", thread_id)
          .single();
        if (!thread) {
          return NextResponse.json(
            { error: "Thread not found" },
            { status: 404 }
          );
        }
        if (thread.user_id) {
          if (user_id !== thread.user_id) {
            return NextResponse.json(
              { error: "Thread access denied" },
              { status: 403 }
            );
          }
        } else if (anonymous_id && thread.anonymous_id !== anonymous_id) {
          return NextResponse.json(
            { error: "Thread access denied" },
            { status: 403 }
          );
        }
      } else if (user_id) {
        const { data: newThread } = await supabase
          .from("chat_threads")
          .insert({
            user_id,
            partner_id: partner_id || null,
            title: lastUserMessage.slice(0, 100) || "New chat",
          })
          .select("id")
          .single();
        resolvedThreadId = newThread?.id ?? null;
        isNewThread = !!newThread?.id;
      } else if (anonymous_id) {
        const { data: newThread } = await supabase
          .from("chat_threads")
          .insert({
            anonymous_id,
            partner_id: partner_id || null,
            title: lastUserMessage.slice(0, 100) || "New chat",
          })
          .select("id")
          .single();
        resolvedThreadId = newThread?.id ?? null;
        isNewThread = !!newThread?.id;
      }

      if (resolvedThreadId) {
        await supabase.from("chat_messages").insert({
          thread_id: resolvedThreadId,
          role: "user",
          content: lastUserMessage,
          channel: "web",
        });
        await supabase
          .from("chat_threads")
          .update({ updated_at: new Date().toISOString() })
          .eq("id", resolvedThreadId);
      }
    }

    const payload: Record<string, unknown> = {
      text: lastUserMessage,
      limit: 20,
      platform: "web",
    };
    if (partner_id) payload.partner_id = partner_id;
    if (user_id) payload.user_id = user_id;
    if (resolvedThreadId) {
      payload.thread_id = resolvedThreadId;
    }
    if (messages && messages.length > 0) {
      payload.messages = messages;
    }
    if (bundle_id) payload.bundle_id = bundle_id;
    if (order_id) payload.order_id = order_id;
    if (debugRequested === true) payload.debug = true;

    const chatUrl = `${ORCHESTRATOR_URL}/api/v1/chat${streamRequested ? "?stream=true" : ""}`;
    const res = await fetch(chatUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (streamRequested && res.ok && res.body) {
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      const stream = new ReadableStream({
        async start(controller) {
          try {
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
                if (eventType === "done" && eventData && supabase && resolvedThreadId) {
                  try {
                    const data = JSON.parse(eventData) as Record<string, unknown>;
                    const assistantContent = (data.summary ?? data.message ?? "") as string;
                    const adaptiveCard = data.adaptive_card ?? null;
                    await supabase.from("chat_messages").insert({
                      thread_id: resolvedThreadId,
                      role: "assistant",
                      content: assistantContent || null,
                      adaptive_card: adaptiveCard,
                      channel: "web",
                    });
                    const updatePayload: Record<string, string> = { updated_at: new Date().toISOString() };
                    if (isNewThread) {
                      updatePayload.title = deriveThreadTitle(data, lastUserMessage) || lastUserMessage.slice(0, 50) || "New chat";
                    }
                    await supabase.from("chat_threads").update(updatePayload).eq("id", resolvedThreadId);
                    const threadTitle = isNewThread && resolvedThreadId
                      ? deriveThreadTitle(data, lastUserMessage) || lastUserMessage.slice(0, 50) || "New chat"
                      : undefined;
                    const enriched = { ...data, thread_id: resolvedThreadId, ...(threadTitle && { thread_title: threadTitle }) };
                    controller.enqueue(new TextEncoder().encode(`event: done\ndata: ${JSON.stringify(enriched)}\n\n`));
                  } catch {
                    controller.enqueue(new TextEncoder().encode(block + "\n\n"));
                  }
                } else {
                  controller.enqueue(new TextEncoder().encode(block + "\n\n"));
                }
              }
            }
          } finally {
            controller.close();
          }
        },
      });
      return new Response(stream, {
        headers: {
          "Content-Type": "text/event-stream",
          "Cache-Control": "no-cache",
          Connection: "keep-alive",
        },
      });
    }

    if (!res.ok) {
      const text = await res.text();
      return NextResponse.json(
        { error: text || `Orchestrator error: ${res.status}` },
        { status: res.status }
      );
    }

    const data = (await res.json()) as Record<string, unknown>;

    if (supabase && resolvedThreadId) {
      const assistantContent = (data.summary ?? data.message ?? "") as string;
      const adaptiveCard = data.adaptive_card ?? null;
      await supabase.from("chat_messages").insert({
        thread_id: resolvedThreadId,
        role: "assistant",
        content: assistantContent || null,
        adaptive_card: adaptiveCard,
        channel: "web",
      });

      // For new threads, set a human-friendly title from the orchestrator response (e.g. "Planning date night")
      const updatePayload: Record<string, string> = { updated_at: new Date().toISOString() };
      if (isNewThread) {
        updatePayload.title = deriveThreadTitle(data, lastUserMessage) || lastUserMessage.slice(0, 50) || "New chat";
      }

      await supabase
        .from("chat_threads")
        .update(updatePayload)
        .eq("id", resolvedThreadId);
    }

    const threadTitle =
      isNewThread && resolvedThreadId
        ? deriveThreadTitle(data, lastUserMessage) || lastUserMessage.slice(0, 50) || "New chat"
        : undefined;
    const response = {
      ...data,
      thread_id: resolvedThreadId ?? data.thread_id,
      ...(threadTitle && { thread_title: threadTitle }),
    };
    return NextResponse.json(response);
  } catch (err) {
    const msg = err instanceof Error ? err.message : "Chat failed";
    // Fetch failures (e.g. ECONNREFUSED to localhost) → suggest ORCHESTRATOR_URL
    const isConnectionError =
      typeof msg === "string" &&
      (msg.includes("fetch") ||
        msg.includes("ECONNREFUSED") ||
        msg.includes("Failed to fetch"));
    return NextResponse.json(
      {
        error: isConnectionError
          ? "Cannot reach orchestrator. Ensure ORCHESTRATOR_URL is set to your Render orchestrator URL (e.g. https://uso-orchestrator.onrender.com)."
          : msg,
      },
      { status: 500 }
    );
  }
}
