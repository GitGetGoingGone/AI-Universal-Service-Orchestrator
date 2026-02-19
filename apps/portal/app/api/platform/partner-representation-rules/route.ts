import { NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/lib/supabase";
import { isPlatformAdmin } from "@/lib/auth";

export async function GET() {
  try {
    if (!(await isPlatformAdmin())) {
      return NextResponse.json({ detail: "Platform admin access required" }, { status: 403 });
    }

    const supabase = createSupabaseServerClient();
    const { data: rulesData, error } = await supabase
      .from("partner_representation_rules")
      .select("id, partner_id, admin_weight, preferred_protocol")
      .order("created_at", { ascending: true });

    if (error) {
      return NextResponse.json({ detail: error.message }, { status: 500 });
    }

    const rules = rulesData ?? [];
    const partnerIds = [...new Set(rules.map((r: { partner_id: string }) => r.partner_id))];
    let partnerNames: Record<string, string> = {};
    if (partnerIds.length > 0) {
      const { data: partners } = await supabase
        .from("partners")
        .select("id, business_name")
        .in("id", partnerIds);
      partnerNames = (partners ?? []).reduce(
        (acc: Record<string, string>, p: { id: string; business_name?: string }) => {
          acc[p.id] = p.business_name ?? p.id;
          return acc;
        },
        {}
      );
    }

    const rulesWithNames = rules.map((r: { partner_id: string }) => ({
      ...r,
      partner_name: partnerNames[r.partner_id] ?? r.partner_id,
    }));

    return NextResponse.json(rulesWithNames);
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
    const { partner_id, admin_weight, preferred_protocol } = body;

    if (!partner_id) {
      return NextResponse.json({ detail: "partner_id is required" }, { status: 400 });
    }

    const supabase = createSupabaseServerClient();
    const { data, error } = await supabase
      .from("partner_representation_rules")
      .upsert(
        {
          partner_id,
          admin_weight: Math.max(0, Math.min(10, Number(admin_weight ?? 1))),
          preferred_protocol: ["UCP", "MCP", "DB"].includes(String(preferred_protocol ?? "DB"))
            ? String(preferred_protocol).toUpperCase()
            : "DB",
          updated_at: new Date().toISOString(),
        },
        { onConflict: "partner_id" }
      )
      .select()
      .single();

    if (error) {
      return NextResponse.json({ detail: error.message }, { status: 500 });
    }

    return NextResponse.json(data);
  } catch (err) {
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
