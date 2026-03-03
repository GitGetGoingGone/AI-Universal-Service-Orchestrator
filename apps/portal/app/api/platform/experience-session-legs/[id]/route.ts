import { NextResponse } from "next/server";
import { auth } from "@clerk/nextjs/server";
import { createSupabaseServerClient } from "@/lib/supabase";
import { isPlatformAdmin } from "@/lib/auth";

/** PATCH: Override leg status */
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
      return NextResponse.json({ detail: "Leg ID required" }, { status: 400 });
    }

    const body = await request.json();
    const new_status = body?.status;
    if (!new_status || !["pending", "ready", "in_customization", "committed", "failed"].includes(new_status)) {
      return NextResponse.json({ detail: "Invalid status" }, { status: 400 });
    }

    const { userId } = await auth();
    if (!userId) {
      return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
    }

    const supabase = createSupabaseServerClient();
    const { data: admin } = await supabase
      .from("platform_admins")
      .select("id")
      .eq("clerk_user_id", userId)
      .limit(1)
      .single();

    const admin_id = admin?.id;
    if (!admin_id) {
      return NextResponse.json({ detail: "Admin record not found" }, { status: 403 });
    }

    const { data: leg, error: legError } = await supabase
      .from("experience_session_legs")
      .select("id, status")
      .eq("id", id)
      .single();

    if (legError || !leg) {
      return NextResponse.json({ detail: "Leg not found" }, { status: 404 });
    }

    const old_status = leg.status;

    await supabase
      .from("experience_session_legs")
      .update({ status: new_status, updated_at: new Date().toISOString() })
      .eq("id", id);

    await supabase.from("experience_session_leg_overrides").insert({
      leg_id: id,
      admin_id,
      old_status,
      new_status,
    });

    return NextResponse.json({ id, status: new_status });
  } catch (err) {
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
