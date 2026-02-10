import { NextResponse } from "next/server";
import { getPartnerId } from "@/lib/auth";

const DISCOVERY_SERVICE_URL = process.env.DISCOVERY_SERVICE_URL ?? process.env.NEXT_PUBLIC_DISCOVERY_SERVICE_URL ?? "";

export async function POST(request: Request) {
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

  let body: { scope?: string; product_id?: string; product_ids?: string[]; targets?: string[] };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ detail: "Invalid JSON" }, { status: 400 });
  }

  const scope = body.scope ?? "all";
  const product_id = body.product_id ?? undefined;
  const product_ids = Array.isArray(body.product_ids) ? body.product_ids : undefined;
  const targets = Array.isArray(body.targets) ? body.targets : [];

  const base = DISCOVERY_SERVICE_URL.replace(/\/$/, "");
  const url = `${base}/api/v1/feeds/push`;

  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        scope,
        product_id,
        product_ids,
        targets,
        partner_id: partnerId,
      }),
      cache: "no-store",
    });
    const data = await res.json().catch(() => ({}));
    return NextResponse.json(data, { status: res.status });
  } catch (err) {
    return NextResponse.json(
      { detail: err instanceof Error ? err.message : "Discovery service unavailable" },
      { status: 502 }
    );
  }
}
