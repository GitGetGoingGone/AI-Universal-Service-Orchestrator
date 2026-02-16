import { NextResponse } from "next/server";
import { getSupabase } from "@/lib/supabase";

/**
 * GET /api/orders/[id]
 * Fetch order by id (for checking customer_phone before payment).
 */
export async function GET(
  req: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const supabase = getSupabase();
  if (!supabase) {
    return NextResponse.json(
      { error: "Persistence not configured" },
      { status: 503 }
    );
  }

  const { data: order, error } = await supabase
    .from("orders")
    .select("id, status, payment_status, customer_phone, user_id")
    .eq("id", id)
    .single();

  if (error || !order) {
    return NextResponse.json({ error: "Order not found" }, { status: 404 });
  }

  // Only expose minimal fields for checkout flow (pending orders)
  if (order.status !== "pending" || order.payment_status !== "pending") {
    return NextResponse.json({ error: "Order not available" }, { status: 400 });
  }

  return NextResponse.json({
    id: order.id,
    status: order.status,
    payment_status: order.payment_status,
    customer_phone: order.customer_phone ?? null,
    user_id: order.user_id ?? null,
  });
}
