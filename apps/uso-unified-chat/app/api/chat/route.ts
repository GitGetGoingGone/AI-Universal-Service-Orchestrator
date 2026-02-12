import { NextResponse } from "next/server";

const ORCHESTRATOR_URL =
  process.env.ORCHESTRATOR_URL || "http://localhost:8002";

export async function POST(req: Request) {
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
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "Chat failed" },
      { status: 500 }
    );
  }
}
