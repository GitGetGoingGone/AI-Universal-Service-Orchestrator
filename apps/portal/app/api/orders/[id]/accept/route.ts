import { NextResponse } from "next/server";
import { getPartnerId } from "@/lib/auth";
import { createSupabaseServerClient } from "@/lib/supabase";

export async function POST(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const partnerId = await getPartnerId();
  if (!partnerId) {
    return NextResponse.json({ detail: "No partner account" }, { status: 403 });
  }

  const { id } = await params;
  const body = await (async () => {
    try {
      return await _request.json();
    } catch {
      return {};
    }
  })();
  const prepMins = body.preparation_mins ?? 15;

  const supabase = createSupabaseServerClient();
  const { error } = await supabase
    .from("order_legs")
    .update({
      status: "accepted",
      preparation_mins: Math.max(0, Number(prepMins)),
    })
    .eq("id", id)
    .eq("partner_id", partnerId);

  if (error) {
    return NextResponse.json({ detail: error.message }, { status: 500 });
  }

  return NextResponse.json({ success: true });
}
