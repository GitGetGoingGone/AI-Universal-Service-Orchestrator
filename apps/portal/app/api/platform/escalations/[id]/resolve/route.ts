import { NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/lib/supabase";
import { isPlatformAdmin } from "@/lib/auth";

export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    if (!(await isPlatformAdmin())) {
      return NextResponse.json({ detail: "Platform admin access required" }, { status: 403 });
    }

    const { id } = await params;
    const body = await request.json().catch(() => ({}));
    const resolutionNotes = body?.resolution_notes || "";

    const supabase = createSupabaseServerClient();
    const { data, error } = await supabase
      .from("support_escalations")
      .update({
        status: "resolved",
        resolved_at: new Date().toISOString(),
        resolution_notes: resolutionNotes,
      })
      .eq("id", id)
      .select()
      .single();

    if (error) {
      return NextResponse.json({ detail: error.message }, { status: error.code === "PGRST116" ? 404 : 500 });
    }

    return NextResponse.json(data);
  } catch (err) {
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
