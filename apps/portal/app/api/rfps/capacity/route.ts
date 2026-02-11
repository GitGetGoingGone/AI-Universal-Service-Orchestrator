import { NextResponse } from "next/server";
import { getPartnerId } from "@/lib/auth";

const HUB_NEGOTIATOR_URL = process.env.HUB_NEGOTIATOR_SERVICE_URL || "";

export async function POST(request: Request) {
  const partnerId = await getPartnerId();
  if (!partnerId) {
    return NextResponse.json({ detail: "No partner account" }, { status: 403 });
  }

  if (!HUB_NEGOTIATOR_URL) {
    return NextResponse.json({ detail: "HUB_NEGOTIATOR_SERVICE_URL not configured" }, { status: 503 });
  }

  const body = await request.json();
  const url = `${HUB_NEGOTIATOR_URL.replace(/\/$/, "")}/api/v1/hub-capacity`;

  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...body, partner_id: partnerId }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      return NextResponse.json(data || { detail: "Failed to add capacity" }, { status: res.status });
    }
    return NextResponse.json(data);
  } catch (err) {
    return NextResponse.json({ detail: "Hub negotiator unreachable" }, { status: 503 });
  }
}
