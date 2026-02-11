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
    .from("partner_kb_articles")
    .select("id, title, content, sort_order, is_active, created_at, updated_at")
    .eq("partner_id", partnerId)
    .order("sort_order", { ascending: true })
    .order("created_at", { ascending: true });

  if (error) return NextResponse.json({ detail: error.message }, { status: 500 });
  return NextResponse.json({ articles: data ?? [] });
}

export async function POST(request: Request) {
  const partnerId = await getPartnerId();
  if (!partnerId) {
    return NextResponse.json({ detail: "No partner account" }, { status: 403 });
  }

  const body = await request.json();
  const title = body?.title as string;
  const content = body?.content as string;
  const sortOrder = (body?.sort_order as number) ?? 0;

  if (!title || typeof title !== "string") {
    return NextResponse.json({ detail: "title required" }, { status: 400 });
  }
  if (!content || typeof content !== "string") {
    return NextResponse.json({ detail: "content required" }, { status: 400 });
  }

  const supabase = createSupabaseServerClient();
  const { data, error } = await supabase
    .from("partner_kb_articles")
    .insert({
      partner_id: partnerId,
      title: title.trim(),
      content: content.trim(),
      sort_order: sortOrder,
      is_active: true,
    })
    .select()
    .single();

  if (error) return NextResponse.json({ detail: error.message }, { status: 500 });
  return NextResponse.json(data);
}
