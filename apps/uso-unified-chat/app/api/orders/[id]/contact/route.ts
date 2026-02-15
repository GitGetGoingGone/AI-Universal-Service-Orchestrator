import { NextResponse } from "next/server";
import { getSupabase } from "@/lib/supabase";

/**
 * Update order with customer phone (collected before payment).
 * Only allows update for pending orders.
 */
export async function PATCH(
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

  const body = await req.json().catch(() => ({}));
  const phone = typeof body.phone === "string" ? body.phone.trim() : "";

  if (!phone) {
    return NextResponse.json(
      { error: "phone is required" },
      { status: 400 }
    );
  }

  // Basic E.164-ish validation: digits, optional +, 10-15 chars
  const normalized = phone.replace(/\s/g, "").replace(/^\+/, "");
  if (!/^\d{10,15}$/.test(normalized)) {
    return NextResponse.json(
      { error: "Invalid phone number. Use 10-15 digits, e.g. 5551234567" },
      { status: 400 }
    );
  }

  const { data: order, error: fetchError } = await supabase
    .from("orders")
    .select("id, status, payment_status")
    .eq("id", id)
    .single();

  if (fetchError || !order) {
    return NextResponse.json({ error: "Order not found" }, { status: 404 });
  }

  if (order.status !== "pending" || order.payment_status !== "pending") {
    return NextResponse.json(
      { error: "Order cannot be updated" },
      { status: 400 }
    );
  }

  const { error: updateError } = await supabase
    .from("orders")
    .update({ customer_phone: `+${normalized}` })
    .eq("id", id);

  if (updateError) {
    return NextResponse.json(
      { error: updateError.message },
      { status: 500 }
    );
  }

  return NextResponse.json({ ok: true });
}
