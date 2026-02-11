import { NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/lib/supabase";
import { isPlatformAdmin } from "@/lib/auth";

export async function GET(request: Request) {
  try {
    if (!(await isPlatformAdmin())) {
      return NextResponse.json({ detail: "Platform admin access required" }, { status: 403 });
    }

    const { searchParams } = new URL(request.url);
    const status = searchParams.get("status") || undefined;

    const supabase = createSupabaseServerClient();
    let q = supabase.from("support_escalations").select("*").order("created_at", { ascending: false });
    if (status) {
      q = q.eq("status", status);
    }
    const { data, error } = await q;

    if (error) {
      return NextResponse.json({ detail: error.message }, { status: 500 });
    }

    return NextResponse.json({ escalations: data || [], count: (data || []).length });
  } catch (err) {
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
