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
    .from("partner_members")
    .select("id, email, display_name, role, is_active, invited_at, joined_at")
    .eq("partner_id", partnerId)
    .order("invited_at", { ascending: false });

  if (error) {
    return NextResponse.json({ detail: error.message }, { status: 500 });
  }
  return NextResponse.json({ members: data ?? [] });
}

export async function POST(request: Request) {
  const partnerId = await getPartnerId();
  if (!partnerId) {
    return NextResponse.json({ detail: "No partner account" }, { status: 403 });
  }

  const body = await request.json();
  const email = body?.email as string | undefined;
  const displayName = body?.display_name as string | undefined;
  const role = (body?.role as string) || "member";

  if (!email || typeof email !== "string") {
    return NextResponse.json({ detail: "email is required" }, { status: 400 });
  }

  const validRoles = ["owner", "admin", "member"];
  if (!validRoles.includes(role)) {
    return NextResponse.json({ detail: "Invalid role" }, { status: 400 });
  }

  const supabase = createSupabaseServerClient();
  const { data, error } = await supabase
    .from("partner_members")
    .insert({
      partner_id: partnerId,
      email: email.trim().toLowerCase(),
      display_name: displayName?.trim() || null,
      role,
      is_active: true,
    })
    .select()
    .single();

  if (error) {
    if (error.code === "23505") {
      return NextResponse.json({ detail: "Member already exists" }, { status: 409 });
    }
    return NextResponse.json({ detail: error.message }, { status: 500 });
  }
  return NextResponse.json(data);
}
