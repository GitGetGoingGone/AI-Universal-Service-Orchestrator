import { NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/lib/supabase";
import { isPlatformAdmin } from "@/lib/auth";

export async function GET() {
  try {
    if (!(await isPlatformAdmin())) {
      return NextResponse.json({ detail: "Platform admin access required" }, { status: 403 });
    }

    const supabase = createSupabaseServerClient();
    const { data, error } = await supabase
      .from("platform_admins")
      .select("id, clerk_user_id, user_id, scope, created_at")
      .order("created_at", { ascending: false });

    if (error) {
      return NextResponse.json({ detail: error.message }, { status: 500 });
    }

    return NextResponse.json({ admins: data ?? [] });
  } catch (err) {
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}

export async function POST(request: Request) {
  try {
    if (!(await isPlatformAdmin())) {
      return NextResponse.json({ detail: "Platform admin access required" }, { status: 403 });
    }

    const body = await request.json();
    const { clerk_user_id } = body;

    if (!clerk_user_id || typeof clerk_user_id !== "string") {
      return NextResponse.json(
        { detail: "clerk_user_id is required" },
        { status: 400 }
      );
    }

    const supabase = createSupabaseServerClient();

    // Get or create user for this clerk ID (users.id can be UUID - we use clerk_user_id for lookup)
    const { data: existing } = await supabase
      .from("platform_admins")
      .select("id")
      .eq("clerk_user_id", clerk_user_id)
      .single();

    if (existing) {
      return NextResponse.json(
        { detail: "Admin already exists" },
        { status: 400 }
      );
    }

    // Insert with clerk_user_id (user_id can be null)
    const { data, error } = await supabase
      .from("platform_admins")
      .insert({
        clerk_user_id: clerk_user_id.trim(),
        user_id: null,
        scope: "all",
      })
      .select("id")
      .single();

    if (error) {
      return NextResponse.json({ detail: error.message }, { status: 500 });
    }

    return NextResponse.json({ id: data.id });
  } catch (err) {
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
