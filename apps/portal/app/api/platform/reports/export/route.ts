import { NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/lib/supabase";
import { isPlatformAdmin } from "@/lib/auth";

export async function GET(request: Request) {
  try {
    if (!(await isPlatformAdmin())) {
      return NextResponse.json({ detail: "Platform admin access required" }, { status: 403 });
    }

    const { searchParams } = new URL(request.url);
    const type = searchParams.get("type") || "partners";
    const format = searchParams.get("format") || "csv";

    const supabase = createSupabaseServerClient();

    if (type === "partners") {
      const { data, error } = await supabase
        .from("partners")
        .select("id, business_name, contact_email, verification_status, is_active, created_at")
        .order("created_at", { ascending: false });

      if (error) {
        return NextResponse.json({ detail: error.message }, { status: 500 });
      }

      const rows = data || [];
      const csv = [
        "id,business_name,contact_email,verification_status,is_active,created_at",
        ...rows.map(
          (r) =>
            `${r.id},"${(r.business_name || "").replace(/"/g, '""')}","${(r.contact_email || "").replace(/"/g, '""')}",${r.verification_status || ""},${r.is_active},${r.created_at}`
        ),
      ].join("\n");

      return new NextResponse(csv, {
        headers: {
          "Content-Type": "text/csv",
          "Content-Disposition": `attachment; filename="partners-${new Date().toISOString().slice(0, 10)}.csv"`,
        },
      });
    }

    if (type === "orders") {
      const { data, error } = await supabase
        .from("orders")
        .select("id, total_amount, currency, status, created_at")
        .order("created_at", { ascending: false })
        .limit(1000);

      if (error) {
        return NextResponse.json({ detail: error.message }, { status: 500 });
      }

      const rows = data || [];
      const csv = [
        "id,total_amount,currency,status,created_at",
        ...rows.map((r) => `${r.id},${r.total_amount},${r.currency},${r.status || ""},${r.created_at}`),
      ].join("\n");

      return new NextResponse(csv, {
        headers: {
          "Content-Type": "text/csv",
          "Content-Disposition": `attachment; filename="orders-${new Date().toISOString().slice(0, 10)}.csv"`,
        },
      });
    }

    if (type === "escalations") {
      const { data, error } = await supabase
        .from("support_escalations")
        .select("id, conversation_ref, classification, status, assigned_to, assigned_to_clerk_id, created_at, resolved_at, resolution_notes")
        .order("created_at", { ascending: false })
        .limit(500);

      if (error) {
        return NextResponse.json({ detail: error.message }, { status: 500 });
      }

      const rows = data || [];
      const csv = [
        "id,conversation_ref,classification,status,assigned_to,assigned_to_clerk_id,created_at,resolved_at,resolution_notes",
        ...rows.map(
          (r) =>
            `${r.id},"${(r.conversation_ref || "").replace(/"/g, '""')}",${r.classification},${r.status},${r.assigned_to || ""},${r.assigned_to_clerk_id || ""},${r.created_at},${r.resolved_at || ""},"${(r.resolution_notes || "").replace(/"/g, '""')}"`
        ),
      ].join("\n");

      return new NextResponse(csv, {
        headers: {
          "Content-Type": "text/csv",
          "Content-Disposition": `attachment; filename="escalations-${new Date().toISOString().slice(0, 10)}.csv"`,
        },
      });
    }

    return NextResponse.json({ detail: "type must be partners, orders, or escalations" }, { status: 400 });
  } catch (err) {
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
