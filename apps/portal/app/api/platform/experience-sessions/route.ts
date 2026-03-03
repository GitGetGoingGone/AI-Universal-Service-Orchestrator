import { NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/lib/supabase";
import { isPlatformAdmin } from "@/lib/auth";

export async function GET(request: Request) {
  try {
    if (!(await isPlatformAdmin())) {
      return NextResponse.json({ detail: "Platform admin access required" }, { status: 403 });
    }

    const { searchParams } = new URL(request.url);
    const thread_id = searchParams.get("thread_id") ?? undefined;
    const user_id = searchParams.get("user_id") ?? undefined;
    const status = searchParams.get("status") ?? undefined;
    const limit = Math.min(100, Math.max(1, parseInt(searchParams.get("limit") || "50", 10)));
    const offset = Math.max(0, parseInt(searchParams.get("offset") || "0", 10));

    const supabase = createSupabaseServerClient();
    let q = supabase
      .from("experience_sessions")
      .select("*")
      .order("created_at", { ascending: false })
      .range(offset, offset + limit - 1);
    if (thread_id) q = q.eq("thread_id", thread_id);
    if (user_id) q = q.eq("user_id", user_id);
    if (status) q = q.eq("status", status);

    const { data: sessions, error } = await q;

    if (error) {
      return NextResponse.json({ detail: error.message }, { status: 500 });
    }
    return NextResponse.json({ sessions: sessions ?? [] });
  } catch (err) {
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
