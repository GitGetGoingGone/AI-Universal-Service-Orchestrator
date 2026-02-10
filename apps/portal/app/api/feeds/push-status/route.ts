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
      { next_acp_push_allowed_at: null },
      { status: 200 }
    );
  }

  const base = DISCOVERY_SERVICE_URL.replace(/\/$/, "");
  const url = `${base}/api/v1/feeds/push-status?partner_id=${encodeURIComponent(partnerId)}`;

  try {
    const res = await fetch(url, { cache: "no-store" });
    const data = await res.json().catch(() => ({}));
    return NextResponse.json({
      next_acp_push_allowed_at: data.next_acp_push_allowed_at ?? null,
    });
  } catch {
    return NextResponse.json({ next_acp_push_allowed_at: null });
  }
}
