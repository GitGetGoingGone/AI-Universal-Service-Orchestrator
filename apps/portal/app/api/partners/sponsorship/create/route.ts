import { NextResponse } from "next/server";
import { getPartnerId } from "@/lib/auth";

const PAYMENT_SERVICE_URL = process.env.PAYMENT_SERVICE_URL || "";

export async function POST(request: Request) {
  try {
    const partnerId = await getPartnerId();
    if (!partnerId) {
      return NextResponse.json({ detail: "No partner account" }, { status: 403 });
    }

    const body = await request.json();
    const { product_id, duration_days } = body;
    if (!product_id || typeof product_id !== "string") {
      return NextResponse.json({ detail: "product_id required" }, { status: 400 });
    }
    const days = Number(duration_days ?? 7);
    if (days < 1 || days > 365) {
      return NextResponse.json({ detail: "duration_days must be 1-365" }, { status: 400 });
    }

    if (!PAYMENT_SERVICE_URL) {
      return NextResponse.json(
        { detail: "PAYMENT_SERVICE_URL not configured" },
        { status: 503 }
      );
    }

    const res = await fetch(`${PAYMENT_SERVICE_URL}/api/v1/sponsorship/create`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        product_id,
        partner_id: partnerId,
        duration_days: days,
      }),
    });

    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      return NextResponse.json(
        { detail: data.detail || "Sponsorship creation failed" },
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
