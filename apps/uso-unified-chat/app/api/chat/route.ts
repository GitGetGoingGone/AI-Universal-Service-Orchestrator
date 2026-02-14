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
    } = body as {
      messages?: { role: string; content: string }[];
      partner_id?: string;
      user_id?: string;
      thread_id?: string;
      anonymous_id?: string;
    };

    const lastUserMessage =
      messages
        ?.filter((m) => m.role === "user")
        .pop()?.content || "Find products";

    const supabase = getSupabase();
    let resolvedThreadId = thread_id;

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
      }

      if (resolvedThreadId) {
        await supabase.from("chat_messages").insert({
          thread_id: resolvedThreadId,
          role: "user",
          content: lastUserMessage,
          channel: "web",
        });
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

    const res = await fetch(`${ORCHESTRATOR_URL}/api/v1/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

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
    }

    const response = { ...data, thread_id: resolvedThreadId ?? data.thread_id };
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
