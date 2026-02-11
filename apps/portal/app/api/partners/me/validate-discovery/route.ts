import { NextResponse } from "next/server";
import { getPartnerId } from "@/lib/auth";

const DISCOVERY_SERVICE_URL = process.env.DISCOVERY_SERVICE_URL ?? process.env.NEXT_PUBLIC_DISCOVERY_SERVICE_URL ?? "";

export async function GET() {
  const partnerId = await getPartnerId();
  if (!partnerId) {
    return NextResponse.json({ detail: "No partner account" }, { status: 403 });
  }

  if (!DISCOVERY_SERVICE_URL) {
    return NextResponse.json(
      { detail: "Discovery service URL not configured (DISCOVERY_SERVICE_URL)" },
      { status: 503 }
    );
  }

  const base = DISCOVERY_SERVICE_URL.replace(/\/$/, "");
  const url = `${base}/api/v1/partners/${encodeURIComponent(partnerId)}/validate-discovery`;

  try {
    const res = await fetch(url, { cache: "no-store" });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      return NextResponse.json(data, { status: res.status });
    }
    return NextResponse.json(data);
  } catch (err) {
    return NextResponse.json(
      { detail: err instanceof Error ? err.message : "Discovery service unavailable" },
      { status: 502 }
    );
  }
}
