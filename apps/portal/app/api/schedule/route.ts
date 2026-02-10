import { NextResponse } from "next/server";
import { getPartnerId } from "@/lib/auth";
import { createSupabaseServerClient } from "@/lib/supabase";

export async function GET() {
  const partnerId = await getPartnerId();
  if (!partnerId) {
    return NextResponse.json({ detail: "No partner account" }, { status: 403 });
  }

  const supabase = createSupabaseServerClient();
  const { data, error } = await supabase
    .from("partner_schedules")
    .select("*")
    .eq("partner_id", partnerId)
    .eq("is_active", true)
    .order("day_of_week");

  if (error) {
    return NextResponse.json({ detail: error.message }, { status: 500 });
  }

  return NextResponse.json({ schedule: data ?? [] });
}

export async function PUT(request: Request) {
  const partnerId = await getPartnerId();
  if (!partnerId) {
    return NextResponse.json({ detail: "No partner account" }, { status: 403 });
  }

  const body = await request.json();
  const { slots } = body as { slots: { day_of_week: number; start_time: string; end_time: string }[] };

  if (!Array.isArray(slots)) {
    return NextResponse.json({ detail: "slots array required" }, { status: 400 });
  }

  const supabase = createSupabaseServerClient();

  await supabase.from("partner_schedules").delete().eq("partner_id", partnerId);

  if (slots.length > 0) {
    const rows = slots.map((s) => ({
      partner_id: partnerId,
      day_of_week: s.day_of_week,
      start_time: s.start_time,
      end_time: s.end_time,
      is_active: true,
    }));

    const { error } = await supabase.from("partner_schedules").insert(rows);
    if (error) {
      return NextResponse.json({ detail: error.message }, { status: 500 });
    }
  }

  return NextResponse.json({ success: true });
}
