import { NextResponse } from "next/server";
import { auth } from "@clerk/nextjs/server";

const ORCHESTRATOR_URL =
  process.env.ORCHESTRATOR_SERVICE_URL || "https://uso-orchestrator.onrender.com";

export async function POST(request: Request) {
  try {
    const { userId } = await auth();
    if (!userId) {
      return NextResponse.json({ detail: "Sign in required" }, { status: 401 });
    }

    const body = await request.json();
    const { order_id } = body;
    if (!order_id || typeof order_id !== "string") {
      return NextResponse.json(
        { detail: "order_id required" },
        { status: 400 }
      );
    }

    const res = await fetch(`${ORCHESTRATOR_URL}/api/v1/payment/create`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ order_id }),
    });

    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      return NextResponse.json(
        { detail: data.detail || "Payment intent creation failed" },
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
