import { NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/lib/supabase";
import { isPlatformAdmin } from "@/lib/auth";

/** POST: Send message to partner for leg. Stub – wires to existing notification infra when available. */
export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    if (!(await isPlatformAdmin())) {
      return NextResponse.json({ detail: "Platform admin access required" }, { status: 403 });
    }

    const { id } = await params;
    if (!id) {
      return NextResponse.json({ detail: "Leg ID required" }, { status: 400 });
    }

    const body = await request.json();
    const message = body?.message;
    const channel = body?.channel ?? "email";

    if (!message || typeof message !== "string") {
      return NextResponse.json({ detail: "message required" }, { status: 400 });
    }

    const supabase = createSupabaseServerClient();
    const { data: leg } = await supabase
      .from("experience_session_legs")
      .select("id, partner_id")
      .eq("id", id)
      .single();

    if (!leg?.partner_id) {
      return NextResponse.json({ detail: "Leg not found" }, { status: 404 });
    }

    // TODO: Wire to existing notification/email infra
    // For now, acknowledge receipt. Store in partner_messages if table exists.
    return NextResponse.json({
      ok: true,
      leg_id: id,
      message: "Message queued (notification infra to be wired)",
      channel,
    });
  } catch (err) {
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
