import { NextResponse } from "next/server";

const ORCHESTRATOR_URL =
  process.env.ORCHESTRATOR_URL || "http://localhost:8002";

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const res = await fetch(`${ORCHESTRATOR_URL}/api/v1/bundle/replace`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        bundle_id: body.bundle_id,
        leg_id: body.leg_id,
        new_product_id: body.new_product_id ?? body.product_id,
      }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      return NextResponse.json(
        { error: data.detail || data.error || `HTTP ${res.status}` },
        { status: res.status }
      );
    }
    return NextResponse.json(data);
  } catch (err) {
    return NextResponse.json(
      {
        error:
          err instanceof Error ? err.message : "Replace in bundle failed",
      },
      { status: 500 }
    );
  }
}
