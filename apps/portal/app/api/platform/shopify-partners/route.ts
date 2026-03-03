import { NextResponse } from "next/server";
import { isPlatformAdmin } from "@/lib/auth";

const DISCOVERY_SERVICE_URL =
  process.env.DISCOVERY_SERVICE_URL ?? process.env.NEXT_PUBLIC_DISCOVERY_SERVICE_URL ?? "";

export async function POST(request: Request) {
  try {
    if (!(await isPlatformAdmin())) {
      return NextResponse.json({ detail: "Platform admin access required" }, { status: 403 });
    }

    if (!DISCOVERY_SERVICE_URL) {
      return NextResponse.json(
        { detail: "Discovery service URL not configured (DISCOVERY_SERVICE_URL)" },
        { status: 503 }
      );
    }

    const body = await request.json();
    const {
      shop_url,
      mcp_endpoint,
      display_name,
      supported_capabilities,
      available_to_customize,
      price_premium_percent,
      access_token,
    } = body;

    if (!shop_url || !mcp_endpoint) {
      return NextResponse.json(
        { detail: "shop_url and mcp_endpoint are required" },
        { status: 400 }
      );
    }

    const payload: Record<string, unknown> = {
      shop_url: String(shop_url).trim().toLowerCase().replace(/^https?:\/\//, "").replace(/\/$/, ""),
      mcp_endpoint: String(mcp_endpoint).trim().replace(/\/$/, ""),
      display_name: display_name ? String(display_name).trim() : String(shop_url).trim(),
      supported_capabilities: Array.isArray(supported_capabilities)
        ? supported_capabilities
        : typeof supported_capabilities === "string"
          ? supported_capabilities
              .split(",")
              .map((s: string) => s.trim())
              .filter(Boolean)
          : [],
      available_to_customize: Boolean(available_to_customize),
      price_premium_percent:
        price_premium_percent != null ? Number(price_premium_percent) : 0,
    };
    if (access_token != null && String(access_token).trim()) {
      payload.access_token = String(access_token).trim();
    }

    const base = DISCOVERY_SERVICE_URL.replace(/\/$/, "");
    const res = await fetch(`${base}/api/v1/admin/partners`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      return NextResponse.json(
        { detail: (data as { detail?: string }).detail || data?.error || "Discovery service error" },
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
