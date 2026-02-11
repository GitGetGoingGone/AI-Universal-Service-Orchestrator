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
    .from("partner_kb_articles")
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
  const content = body?.content as string | undefined;
  const sortOrder = body?.sort_order as number | undefined;
  const isActive = body?.is_active as boolean | undefined;

  const updates: Record<string, unknown> = { updated_at: new Date().toISOString() };
  if (title !== undefined) updates.title = title;
  if (content !== undefined) updates.content = content;
  if (sortOrder !== undefined) updates.sort_order = sortOrder;
  if (isActive !== undefined) updates.is_active = isActive;

  const supabase = createSupabaseServerClient();
  const { data, error } = await supabase
    .from("partner_kb_articles")
    .update(updates)
    .eq("id", id)
    .eq("partner_id", partnerId)
    .select()
    .single();

  if (error) return NextResponse.json({ detail: error.message }, { status: 500 });
  return NextResponse.json(data);
}

export async function DELETE(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const partnerId = await getPartnerId();
  if (!partnerId) {
    return NextResponse.json({ detail: "No partner account" }, { status: 403 });
  }

  const { id } = await params;
  const supabase = createSupabaseServerClient();
  const { error } = await supabase
    .from("partner_kb_articles")
    .delete()
    .eq("id", id)
    .eq("partner_id", partnerId);

  if (error) return NextResponse.json({ detail: error.message }, { status: 500 });
  return new NextResponse(null, { status: 204 });
}
