import { NextResponse } from "next/server";
import { isPlatformAdmin } from "@/lib/auth";

const HUB_NEGOTIATOR_URL = process.env.HUB_NEGOTIATOR_SERVICE_URL || "";

export async function GET(request: Request) {
  if (!(await isPlatformAdmin())) {
    return NextResponse.json({ detail: "Platform admin access required" }, { status: 403 });
  }

  if (!HUB_NEGOTIATOR_URL) {
    return NextResponse.json({ detail: "HUB_NEGOTIATOR_SERVICE_URL not configured" }, { status: 503 });
  }

  const { searchParams } = new URL(request.url);
  const status = searchParams.get("status") || "open";
  const url = `${HUB_NEGOTIATOR_URL.replace(/\/$/, "")}/api/v1/rfps?status=${status}`;

  try {
    const res = await fetch(url);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      return NextResponse.json(data || { detail: "Hub negotiator error" }, { status: res.status });
    }
    return NextResponse.json(data);
  } catch (err) {
    return NextResponse.json({ detail: "Hub negotiator unreachable" }, { status: 503 });
  }
}

export async function POST(request: Request) {
  if (!(await isPlatformAdmin())) {
    return NextResponse.json({ detail: "Platform admin access required" }, { status: 403 });
  }

  if (!HUB_NEGOTIATOR_URL) {
    return NextResponse.json({ detail: "HUB_NEGOTIATOR_SERVICE_URL not configured" }, { status: 503 });
  }

  const body = await request.json();
  const url = `${HUB_NEGOTIATOR_URL.replace(/\/$/, "")}/api/v1/rfps`;

  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      return NextResponse.json(data || { detail: "Failed to create RFP" }, { status: res.status });
    }
    return NextResponse.json(data);
  } catch (err) {
    return NextResponse.json({ detail: "Hub negotiator unreachable" }, { status: 503 });
  }
}
