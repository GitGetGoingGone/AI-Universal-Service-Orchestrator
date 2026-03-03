import { NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/lib/supabase";
import { isPlatformAdmin } from "@/lib/auth";

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
    const {
      shop_url,
      mcp_endpoint,
      display_name,
      supported_capabilities,
      available_to_customize,
      price_premium_percent,
    } = body;

    const supabase = createSupabaseServerClient();

    // Get current row to find internal_agent_registry_id
    const { data: row, error: fetchError } = await supabase
      .from("shopify_curated_partners")
      .select("id, internal_agent_registry_id")
      .eq("id", id)
      .single();

    if (fetchError || !row) {
      return NextResponse.json({ detail: "Shopify partner not found" }, { status: 404 });
    }

    const registryId = row.internal_agent_registry_id as string | null;
    const updates: Record<string, unknown> = { updated_at: new Date().toISOString() };

    if (shop_url != null && String(shop_url).trim()) {
      updates.shop_url = String(shop_url).trim().toLowerCase().replace(/^https?:\/\//, "").replace(/\/$/, "");
    }
    if (mcp_endpoint != null && String(mcp_endpoint).trim()) {
      updates.mcp_endpoint = String(mcp_endpoint).trim().replace(/\/$/, "");
    }
    if (supported_capabilities !== undefined) {
      updates.supported_capabilities = Array.isArray(supported_capabilities)
        ? supported_capabilities
        : typeof supported_capabilities === "string"
          ? supported_capabilities.split(",").map((s: string) => s.trim()).filter(Boolean)
          : [];
    }
    if (price_premium_percent != null) {
      updates.price_premium_percent = Number(price_premium_percent);
    }

    if (Object.keys(updates).length > 1) {
      const { error: updateError } = await supabase
        .from("shopify_curated_partners")
        .update(updates)
        .eq("id", id);

      if (updateError) {
        return NextResponse.json({ detail: updateError.message }, { status: 500 });
      }
    }

    if (registryId && (display_name != null || available_to_customize !== undefined)) {
      const registryUpdates: Record<string, unknown> = { updated_at: new Date().toISOString() };
      if (display_name != null) registryUpdates.display_name = String(display_name).trim();
      if (available_to_customize !== undefined) registryUpdates.available_to_customize = Boolean(available_to_customize);

      await supabase
        .from("internal_agent_registry")
        .update(registryUpdates)
        .eq("id", registryId);
    }

    return NextResponse.json({ id, ok: true });
  } catch (err) {
    return NextResponse.json(
      { detail: err instanceof Error ? err.message : "Internal server error" },
      { status: 500 }
    );
  }
}
