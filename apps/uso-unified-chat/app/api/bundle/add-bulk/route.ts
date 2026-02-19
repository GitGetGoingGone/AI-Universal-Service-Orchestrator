import { NextResponse } from "next/server";

const ORCHESTRATOR_URL =
  process.env.ORCHESTRATOR_URL || "http://localhost:8002";

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const res = await fetch(`${ORCHESTRATOR_URL}/api/v1/bundle/add-bulk`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const errMsg = typeof data.detail === "object" && data.detail?.message
        ? data.detail.message
        : typeof data.detail === "string"
          ? data.detail
          : data.error || `HTTP ${res.status}`;
      return NextResponse.json(
        { error: errMsg, detail: data.detail },
        { status: res.status }
      );
    }
    return NextResponse.json(data);
  } catch (err) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "Bulk add to bundle failed" },
      { status: 500 }
    );
  }
}
