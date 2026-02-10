import { NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/lib/supabase";
import { isPlatformAdmin } from "@/lib/auth";

export async function GET(request: Request) {
  try {
    if (!(await isPlatformAdmin())) {
      return NextResponse.json({ detail: "Platform admin access required" }, { status: 403 });
    }
    const { searchParams } = new URL(request.url);
    const status = searchParams.get("status"); // pending | approved | all

    const supabase = createSupabaseServerClient();
    let query = supabase
      .from("partners")
      .select("id, business_name, contact_email, business_type, verification_status, is_active, created_at")
      .order("created_at", { ascending: false });

    if (status === "pending") {
      query = query.eq("verification_status", "pending");
    } else if (status === "approved") {
      query = query.eq("verification_status", "approved");
    }

    const { data, error } = await query;

    if (error) {
      return NextResponse.json({ detail: error.message }, { status: 500 });
    }

    return NextResponse.json({ partners: data ?? [] });
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
    const { business_name, contact_email, business_type } = body;

    if (!business_name || !contact_email) {
      return NextResponse.json(
        { detail: "business_name and contact_email are required" },
        { status: 400 }
      );
    }

    const supabase = createSupabaseServerClient();
    const { data, error } = await supabase
      .from("partners")
      .insert({
        business_name,
        contact_email,
        business_type: business_type || null,
        verification_status: "approved",
        is_active: true,
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
