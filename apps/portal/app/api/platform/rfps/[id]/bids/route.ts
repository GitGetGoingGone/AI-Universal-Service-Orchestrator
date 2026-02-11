import { NextResponse } from "next/server";
import { isPlatformAdmin } from "@/lib/auth";

const HUB_NEGOTIATOR_URL = process.env.HUB_NEGOTIATOR_SERVICE_URL || "";

export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  if (!(await isPlatformAdmin())) {
    return NextResponse.json({ detail: "Platform admin access required" }, { status: 403 });
  }

  if (!HUB_NEGOTIATOR_URL) {
    return NextResponse.json({ detail: "HUB_NEGOTIATOR_SERVICE_URL not configured" }, { status: 503 });
  }

  const { id } = await params;
  const url = `${HUB_NEGOTIATOR_URL.replace(/\/$/, "")}/api/v1/rfps/${id}/bids`;

  try {
    const res = await fetch(url);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      return NextResponse.json(data || { detail: "Failed to list bids" }, { status: res.status });
    }
    return NextResponse.json(data);
  } catch (err) {
    return NextResponse.json({ detail: "Hub negotiator unreachable" }, { status: 503 });
  }
}
