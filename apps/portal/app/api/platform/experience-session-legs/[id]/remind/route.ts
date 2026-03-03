import { NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/lib/supabase";
import { isPlatformAdmin } from "@/lib/auth";

/** POST: Trigger reminder to partner. Stub – wires to task-queue/cron when available. */
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

    const body = await request.json().catch(() => ({}));
    const delay_hours = body?.delay_hours ?? 0;

    const supabase = createSupabaseServerClient();
    const { data: leg } = await supabase
      .from("experience_session_legs")
      .select("id, partner_id")
      .eq("id", id)
      .single();

    if (!leg?.partner_id) {
      return NextResponse.json({ detail: "Leg not found" }, { status: 404 });
    }

    // TODO: Create scheduled task (task-queue or cron) to send reminder
    return NextResponse.json({
      ok: true,
      leg_id: id,
      delay_hours,
      message: "Reminder scheduled (task-queue to be wired)",
    });
  } catch (err) {
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
