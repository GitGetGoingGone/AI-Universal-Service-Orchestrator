import { NextResponse } from "next/server";

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
    const { provider, messages } = body as {
      provider?: string;
      messages?: { role: string; content: string }[];
    };

    const lastUserMessage =
      messages
        ?.filter((m) => m.role === "user")
        .pop()?.content || "Find products";

    const res = await fetch(`${ORCHESTRATOR_URL}/api/v1/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: lastUserMessage,
        limit: 20,
        platform: provider || "chatgpt",
      }),
    });

    if (!res.ok) {
      const text = await res.text();
      return NextResponse.json(
        { error: text || `Orchestrator error: ${res.status}` },
        { status: res.status }
      );
    }

    const data = await res.json();
    return NextResponse.json(data);
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
