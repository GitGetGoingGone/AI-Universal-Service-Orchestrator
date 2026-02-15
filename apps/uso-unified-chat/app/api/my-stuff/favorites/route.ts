import { NextResponse } from "next/server";
import { auth } from "@clerk/nextjs/server";
import { getSupabase } from "@/lib/supabase";

/**
 * POST /api/my-stuff/favorites
 * Add a favorite. Body: { item_type?, item_id, item_name?, anonymous_id? }
 */
export async function POST(req: Request) {
  const supabase = getSupabase();
  if (!supabase) {
    return NextResponse.json(
      { error: "Persistence not configured" },
      { status: 503 }
    );
  }

  const body = await req.json().catch(() => ({}));
  const {
    item_type = "product",
    item_id,
    item_name,
    anonymous_id,
  } = body as {
    item_type?: string;
    item_id?: string;
    item_name?: string;
    anonymous_id?: string;
  };

  if (!item_id) {
    return NextResponse.json({ error: "item_id required" }, { status: 400 });
  }

  let userId: string | null = null;
  const { userId: clerkUserId } = await auth();
  if (clerkUserId) {
    const { data: user } = await supabase
      .from("users")
      .select("id")
      .eq("clerk_user_id", clerkUserId)
      .limit(1)
      .single();
    userId = user?.id ?? null;
  }

  if (!userId && !anonymousId) {
    return NextResponse.json(
      { error: "Sign in or provide anonymous_id" },
      { status: 400 }
    );
  }

  const row: Record<string, unknown> = {
    item_type,
    item_id: String(item_id),
    item_name: item_name || null,
    item_metadata: {},
  };
  if (userId) row.user_id = userId;
  else row.anonymous_id = anonymousId;

  const { data, error } = await supabase
    .from("user_favorites")
    .insert(row)
    .select("id")
    .single();

  if (error) {
    if (error.code === "23505") return NextResponse.json({ ok: true });
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
  return NextResponse.json({ id: data?.id, ok: true });
}
