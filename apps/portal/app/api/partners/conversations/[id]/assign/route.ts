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
  const raw = body?.assigned_to_member_id as string | null | undefined;
  const assignedToMemberId = raw === "" || raw === null || raw === undefined ? null : raw;

  const supabase = createSupabaseServerClient();

  let member: { id: string } | null = null;
  if (assignedToMemberId) {
    const res = await supabase
      .from("partner_members")
      .select("id")
      .eq("id", assignedToMemberId)
      .eq("partner_id", partnerId)
      .single();
    member = res.data ?? null;
  }

  if (assignedToMemberId && !member) {
    return NextResponse.json({ detail: "Invalid team member" }, { status: 400 });
  }

  const { data, error } = await supabase
    .from("conversations")
    .update({ assigned_to_member_id: assignedToMemberId })
    .eq("id", id)
    .eq("partner_id", partnerId)
    .select()
    .single();

  if (error) return NextResponse.json({ detail: error.message }, { status: 500 });
  return NextResponse.json(data);
}
