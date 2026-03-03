import { NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/lib/supabase";
import { isPlatformAdmin } from "@/lib/auth";

const DISCOVERY_SERVICE_URL =
  process.env.DISCOVERY_SERVICE_URL ?? process.env.NEXT_PUBLIC_DISCOVERY_SERVICE_URL ?? "";

export async function GET() {
  try {
    if (!(await isPlatformAdmin())) {
      return NextResponse.json({ detail: "Platform admin access required" }, { status: 403 });
    }

    const supabase = createSupabaseServerClient();
    const { data, error } = await supabase
      .from("internal_agent_registry")
      .select("id, base_url, display_name, enabled, available_to_customize, price_premium_percent, access_token_vault_ref, created_at, updated_at")
      .eq("transport_type", "UCP")
      .order("display_name");

    if (error) {
      return NextResponse.json({ detail: error.message }, { status: 500 });
    }

    const list = (data ?? []).map((row: Record<string, unknown>) => ({
      ...row,
      has_token: Boolean((row as { access_token_vault_ref?: string }).access_token_vault_ref),
    }));
    return NextResponse.json({ ucp_partners: list });
  } catch (err) {
    return NextResponse.json(
      { detail: err instanceof Error ? err.message : "Internal server error" },
      { status: 500 }
    );
  }
}

export async function POST(request: Request) {
  try {
    if (!(await isPlatformAdmin())) {
      return NextResponse.json({ detail: "Platform admin access required" }, { status: 403 });
    }

    const body = await request.json();
    const {
      base_url,
      display_name,
      manifest_json,
      price_premium_percent,
      available_to_customize,
      access_token,
    } = body;

    if (!DISCOVERY_SERVICE_URL) {
      return NextResponse.json(
        { detail: "Discovery service URL not configured (DISCOVERY_SERVICE_URL)" },
        { status: 503 }
      );
    }

    const payload: Record<string, unknown> = {};
    if (base_url != null && String(base_url).trim()) payload.base_url = String(base_url).trim();
    if (display_name != null && String(display_name).trim()) payload.display_name = String(display_name).trim();
    if (manifest_json != null && String(manifest_json).trim()) payload.manifest_json = String(manifest_json).trim();
    payload.price_premium_percent = price_premium_percent != null ? Number(price_premium_percent) : 0;
    payload.available_to_customize = available_to_customize !== undefined ? Boolean(available_to_customize) : false;
    if (access_token != null && String(access_token).trim()) payload.access_token = String(access_token).trim();

    if (!payload.base_url && !payload.manifest_json) {
      return NextResponse.json(
        { detail: "Provide base_url or manifest_json" },
        { status: 400 }
      );
    }

    const base = DISCOVERY_SERVICE_URL.replace(/\/$/, "");
    const res = await fetch(`${base}/api/v1/admin/ucp-partners`, {
      method: "POST",
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
