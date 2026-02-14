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

    const { data: partnersData, error } = await query;

    if (error) {
      return NextResponse.json({ detail: error.message }, { status: 500 });
    }

    const partners = partnersData ?? [];
    const partnerIds = partners.map((p: { id: string }) => p.id);
    let chatConfigs: { partner_id: string; chat_widget_enabled?: boolean; admin_e2e_enabled?: boolean }[] = [];
    if (partnerIds.length > 0) {
      const { data } = await supabase
        .from("partner_chat_config")
        .select("partner_id, chat_widget_enabled, admin_e2e_enabled")
        .in("partner_id", partnerIds);
      chatConfigs = data ?? [];
    }

    const configByPartner = chatConfigs.reduce(
      (acc: Record<string, { chat_widget_enabled: boolean; admin_e2e_enabled: boolean }>, c: { partner_id: string; chat_widget_enabled?: boolean; admin_e2e_enabled?: boolean }) => {
        acc[c.partner_id] = {
          chat_widget_enabled: c.chat_widget_enabled ?? true,
          admin_e2e_enabled: c.admin_e2e_enabled ?? true,
        };
        return acc;
      },
      {}
    );

    const partnersWithConfig = partners.map((p: { id: string }) => ({
      ...p,
      chat_config: configByPartner[p.id] ?? { chat_widget_enabled: true, admin_e2e_enabled: true },
    }));

    return NextResponse.json({ partners: partnersWithConfig });
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
