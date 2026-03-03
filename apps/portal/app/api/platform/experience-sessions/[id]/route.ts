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
      return NextResponse.json({ detail: "Session ID required" }, { status: 400 });
    }

    const supabase = createSupabaseServerClient();
    const { data: session, error: sessionError } = await supabase
      .from("experience_sessions")
      .select("*")
      .eq("id", id)
      .single();

    if (sessionError || !session) {
      return NextResponse.json(
        { detail: sessionError?.message || "Session not found" },
        { status: sessionError?.code === "PGRST116" ? 404 : 500 }
      );
    }

    const { data: legs } = await supabase
      .from("experience_session_legs")
      .select("id, partner_id, product_id, status, shopify_draft_order_id, created_at, updated_at")
      .eq("experience_session_id", id)
      .order("created_at");

    const partnerIds = [...new Set((legs ?? []).map((l) => l.partner_id).filter(Boolean))];
    let partnersMap: Record<string, { business_name?: string }> = {};
    if (partnerIds.length > 0) {
      const { data: partners } = await supabase
        .from("partners")
        .select("id, business_name")
        .in("id", partnerIds);
      (partners ?? []).forEach((p) => {
        partnersMap[p.id] = p;
      });
    }

    const legsWithPartner = (legs ?? []).map((l) => ({
      ...l,
      partner_name: l.partner_id ? partnersMap[l.partner_id]?.business_name : null,
    }));

    return NextResponse.json({
      session: { ...session, legs: legsWithPartner },
    });
  } catch (err) {
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
