import { NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/lib/supabase";
import { isPlatformAdmin } from "@/lib/auth";

export async function GET() {
  try {
    if (!(await isPlatformAdmin())) {
      return NextResponse.json({ detail: "Platform admin access required" }, { status: 403 });
    }

    const supabase = createSupabaseServerClient();

    const [partnersRes, pendingRes] = await Promise.all([
      supabase.from("partners").select("id", { count: "exact", head: true }),
      supabase
        .from("partners")
        .select("id", { count: "exact", head: true })
        .eq("verification_status", "pending"),
    ]);

    return NextResponse.json({
      partners: partnersRes.count ?? 0,
      pendingApprovals: pendingRes.count ?? 0,
    });
  } catch (err) {
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
