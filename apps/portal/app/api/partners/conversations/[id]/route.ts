import { NextResponse } from "next/server";
import { getPartnerId } from "@/lib/auth";
import { createSupabaseServerClient } from "@/lib/supabase";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const partnerId = await getPartnerId();
  if (!partnerId) {
    return NextResponse.json({ detail: "No partner account" }, { status: 403 });
  }

  const { id } = await params;
  const supabase = createSupabaseServerClient();
  const { data, error } = await supabase
    .from("conversations")
    .select("*")
    .eq("id", id)
    .eq("partner_id", partnerId)
    .single();

  if (error || !data) {
    return NextResponse.json({ detail: "Not found" }, { status: 404 });
  }
  return NextResponse.json(data);
}

export async function PATCH(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const partnerId = await getPartnerId();
  if (!partnerId) {
    return NextResponse.json({ detail: "No partner account" }, { status: 403 });
  }

  const { id } = await params;
  const body = await request.json();
  const title = body?.title as string | undefined;
  const status = body?.status as string | undefined;

  const updates: Record<string, unknown> = {};
  if (title !== undefined) updates.title = title;
  if (status !== undefined) updates.status = status;

  if (Object.keys(updates).length === 0) {
    return NextResponse.json({ detail: "No updates" }, { status: 400 });
  }

  const supabase = createSupabaseServerClient();
  const { data, error } = await supabase
    .from("conversations")
    .update(updates)
    .eq("id", id)
    .eq("partner_id", partnerId)
    .select()
    .single();

  if (error) return NextResponse.json({ detail: error.message }, { status: 500 });
  return NextResponse.json(data);
}
