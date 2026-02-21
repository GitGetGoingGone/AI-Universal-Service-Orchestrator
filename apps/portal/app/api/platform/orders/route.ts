import { NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/lib/supabase";
import { isPlatformAdmin } from "@/lib/auth";

export async function GET(request: Request) {
  try {
    if (!(await isPlatformAdmin())) {
      return NextResponse.json({ detail: "Platform admin access required" }, { status: 403 });
    }

    const { searchParams } = new URL(request.url);
    const limit = Math.min(100, Math.max(1, parseInt(searchParams.get("limit") || "50", 10)));
    const offset = Math.max(0, parseInt(searchParams.get("offset") || "0", 10));

    const supabase = createSupabaseServerClient();
    const { data: orders, error } = await supabase
      .from("orders")
      .select(`
        id, bundle_id, user_id, total_amount, currency, status, payment_status, created_at, customer_phone,
        users (email, phone_number, legal_name, display_name)
      `)
      .order("created_at", { ascending: false })
      .range(offset, offset + limit - 1);

    if (error) {
      return NextResponse.json({ detail: error.message }, { status: 500 });
    }

    // Flatten user and add item counts
    const orderIds = (orders ?? []).map((o) => o.id);
    let itemCounts: Record<string, number> = {};
    if (orderIds.length > 0) {
      const { data: items } = await supabase
        .from("order_items")
        .select("order_id")
        .in("order_id", orderIds);
      (items ?? []).forEach((row) => {
        const oid = row.order_id as string;
        itemCounts[oid] = (itemCounts[oid] ?? 0) + 1;
      });
    }

    const users = (orders ?? []).map((o) => (o as { users?: { email?: string; phone_number?: string; legal_name?: string; display_name?: string } | null }).users);
    const ordersWithCount = (orders ?? []).map((o, i) => {
      const u = users[i];
      const row = o as Record<string, unknown>;
      const { users: _u, ...rest } = row;
      return {
        ...rest,
        item_count: itemCounts[o.id] ?? 0,
        customer_name: u?.legal_name || u?.display_name || null,
        customer_email: u?.email ?? null,
        customer_phone: (o as { customer_phone?: string }).customer_phone ?? u?.phone_number ?? null,
      };
    });

    return NextResponse.json({ orders: ordersWithCount });
  } catch (err) {
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
