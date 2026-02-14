import { NextResponse } from "next/server";
import { auth } from "@clerk/nextjs/server";
import { getSupabase } from "@/lib/supabase";

const ORCHESTRATOR_URL =
  process.env.ORCHESTRATOR_URL || "http://localhost:8002";

export async function POST(req: Request) {
  const { userId: clerkUserId } = await auth();
  if (!clerkUserId) {
    return NextResponse.json(
      { error: "Sign in required to link accounts" },
      { status: 401 }
    );
  }

  let body: { provider?: string; platform_user_id?: string };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }

  if (body.provider !== "whatsapp") {
    return NextResponse.json(
      { error: "Only provider=whatsapp supported from web app" },
      { status: 400 }
    );
  }

  if (!body.platform_user_id?.trim()) {
    return NextResponse.json(
      { error: "platform_user_id (phone number) required" },
      { status: 400 }
    );
  }

  try {
    const res = await fetch(`${ORCHESTRATOR_URL}/api/v1/link-account`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        provider: "whatsapp",
        platform_user_id: body.platform_user_id.trim(),
        clerk_user_id: clerkUserId,
      }),
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      return NextResponse.json(
        { error: data.detail ?? data.error ?? `HTTP ${res.status}` },
        { status: res.status }
      );
    }
    return NextResponse.json(data);
  } catch (err) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "Link failed" },
      { status: 500 }
    );
  }
}
