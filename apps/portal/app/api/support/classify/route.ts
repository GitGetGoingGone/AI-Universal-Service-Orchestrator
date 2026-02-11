import { NextResponse } from "next/server";
import { auth } from "@clerk/nextjs/server";

const HYBRID_RESPONSE_URL =
  process.env.HYBRID_RESPONSE_SERVICE_URL || "https://uso-hybrid-response.onrender.com";

export async function POST(request: Request) {
  try {
    const { userId } = await auth();
    if (!userId) {
      return NextResponse.json({ detail: "Sign in required" }, { status: 401 });
    }

    const body = await request.json();
    const { conversation_ref, message_content } = body;
    if (!message_content || typeof message_content !== "string") {
      return NextResponse.json(
        { detail: "message_content required" },
        { status: 400 }
      );
    }

    const res = await fetch(`${HYBRID_RESPONSE_URL}/api/v1/classify-and-route`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        conversation_ref: conversation_ref || `portal-${userId}-${Date.now()}`,
        message_content: message_content.trim(),
      }),
    });

    if (!res.ok) {
      const err = await res.text();
      return NextResponse.json(
        { detail: err || "Classification failed" },
        { status: res.status }
      );
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (err) {
    return NextResponse.json(
      { detail: err instanceof Error ? err.message : "Internal server error" },
      { status: 500 }
    );
  }
}
