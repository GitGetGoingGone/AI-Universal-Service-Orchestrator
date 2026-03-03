import { NextResponse } from "next/server";
import { isPlatformAdmin } from "@/lib/auth";

const DISCOVERY_SERVICE_URL =
  process.env.DISCOVERY_SERVICE_URL ?? process.env.NEXT_PUBLIC_DISCOVERY_SERVICE_URL ?? "";

export async function PATCH(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    if (!(await isPlatformAdmin())) {
      return NextResponse.json({ detail: "Platform admin access required" }, { status: 403 });
    }

    const { id } = await params;
    if (!id) {
      return NextResponse.json({ detail: "ID required" }, { status: 400 });
    }

    const body = await request.json();
    const { display_name, enabled, price_premium_percent, available_to_customize, access_token } = body;

    if (!DISCOVERY_SERVICE_URL) {
      return NextResponse.json(
        { detail: "Discovery service URL not configured (DISCOVERY_SERVICE_URL)" },
        { status: 503 }
      );
    }

    const payload: Record<string, unknown> = {};
    if (display_name !== undefined) payload.display_name = display_name ? String(display_name).trim() : null;
    if (enabled !== undefined) payload.enabled = Boolean(enabled);
    if (price_premium_percent !== undefined) payload.price_premium_percent = Number(price_premium_percent);
    if (available_to_customize !== undefined) payload.available_to_customize = Boolean(available_to_customize);
    if (access_token != null && String(access_token).trim()) payload.access_token = String(access_token).trim();

    const base = DISCOVERY_SERVICE_URL.replace(/\/$/, "");
    const res = await fetch(`${base}/api/v1/admin/ucp-partners/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      return NextResponse.json(
        { detail: (data as { detail?: string }).detail || "Discovery service error" },
        { status: res.status >= 400 && res.status < 500 ? res.status : 502 }
      );
    }

    return NextResponse.json(data);
  } catch (err) {
    return NextResponse.json(
      { detail: err instanceof Error ? err.message : "Internal server error" },
      { status: 500 }
    );
  }
}
