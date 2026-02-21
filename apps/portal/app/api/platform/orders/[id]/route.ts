import { NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/lib/supabase";
import { isPlatformAdmin } from "@/lib/auth";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    if (!(await isPlatformAdmin())) {
      return NextResponse.json({ detail: "Platform admin access required" }, { status: 403 });
    }

    const { id } = await params;
    if (!id) {
      return NextResponse.json({ detail: "Order ID required" }, { status: 400 });
    }

    const supabase = createSupabaseServerClient();

    const { data: order, error: orderError } = await supabase
      .from("orders")
      .select(`
        id, bundle_id, user_id, total_amount, currency, status, payment_status, created_at, paid_at, completed_at, cancelled_at, customer_phone,
        users (id, email, phone_number, legal_name, display_name)
      `)
      .eq("id", id)
      .single();

    if (orderError || !order) {
      return NextResponse.json({ detail: orderError?.message || "Order not found" }, { status: orderError?.code === "PGRST116" ? 404 : 500 });
    }

    let fulfillment_details: Record<string, unknown> | null = null;
    if (order.bundle_id) {
      const { data: bundle } = await supabase
        .from("bundles")
        .select("fulfillment_details")
        .eq("id", order.bundle_id)
        .single();
      fulfillment_details = (bundle?.fulfillment_details as Record<string, unknown>) || null;
    }

    const { data: items } = await supabase
      .from("order_items")
      .select("id, item_name, quantity, unit_price, total_price")
      .eq("order_id", id)
      .order("id");

    const u = (order as { users?: { email?: string; phone_number?: string; legal_name?: string; display_name?: string } | null }).users;
    const customer_name = u?.legal_name || u?.display_name || null;
    const customer_email = u?.email ?? null;
    const customer_phone = (order as { customer_phone?: string }).customer_phone ?? u?.phone_number ?? null;

    const { users: _u, ...orderRest } = order as Record<string, unknown>;
    const detail = {
      ...orderRest,
      customer_name,
      customer_email,
      customer_phone,
      fulfillment_details,
      items: items ?? [],
    };

    return NextResponse.json({ order: detail });
  } catch (err) {
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
