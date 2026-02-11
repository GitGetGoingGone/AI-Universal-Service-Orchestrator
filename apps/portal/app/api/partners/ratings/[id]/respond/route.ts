import { NextResponse } from "next/server";
import { getPartnerId } from "@/lib/auth";
import { createSupabaseServerClient } from "@/lib/supabase";

export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const partnerId = await getPartnerId();
  if (!partnerId) {
    return NextResponse.json({ detail: "No partner account" }, { status: 403 });
  }

  const { id } = await params;
  const body = await request.json();
  const response = body?.partner_response as string | undefined;

  const supabase = createSupabaseServerClient();
  const { data, error } = await supabase
    .from("order_reviews")
    .update({
      partner_response: response ?? "",
      responded_at: new Date().toISOString(),
    })
    .eq("id", id)
    .eq("partner_id", partnerId)
    .select()
    .single();

  if (error) {
    return NextResponse.json({ detail: error.message }, { status: error.code === "PGRST116" ? 404 : 500 });
  }
  return NextResponse.json(data);
}
