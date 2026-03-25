import { NextResponse } from "next/server";

const GATEWAY_URL =
  process.env.NEXT_PUBLIC_GATEWAY_URL || "http://localhost:8002";

/**
 * Proxy multi-agent registry from orchestrator (public catalog for picker UI).
 */
export async function GET() {
  try {
    const res = await fetch(`${GATEWAY_URL.replace(/\/$/, "")}/api/v1/multi-agent/agents`, {
      headers: { Accept: "application/json" },
      signal: AbortSignal.timeout(15000),
    });
    if (!res.ok) {
      const t = await res.text();
      return NextResponse.json(
        { error: t || `Gateway ${res.status}`, enabled: false, agents: [], workflow_order: [] },
        { status: res.status }
      );
    }
    const data = (await res.json()) as Record<string, unknown>;
    return NextResponse.json(data);
  } catch (e) {
    const msg = e instanceof Error ? e.message : "Failed to load agents";
    return NextResponse.json(
      { error: msg, enabled: false, agents: [], workflow_order: [] },
      { status: 503 }
    );
  }
}
