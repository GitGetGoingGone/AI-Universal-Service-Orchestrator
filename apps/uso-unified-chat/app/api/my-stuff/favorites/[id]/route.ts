import { NextResponse } from "next/server";
import { auth } from "@clerk/nextjs/server";
import { getSupabase } from "@/lib/supabase";

/**
 * DELETE /api/my-stuff/favorites/[id]
 * Remove a favorite by id.
 */
export async function DELETE(
  req: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const supabase = getSupabase();
  if (!supabase) {
    return NextResponse.json(
      { error: "Persistence not configured" },
      { status: 503 }
    );
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

  const { searchParams } = new URL(req.url);
  const anonymousId = searchParams.get("anonymous_id");

  let q = supabase.from("user_favorites").delete().eq("id", id);
  if (userId) q = q.eq("user_id", userId);
  else if (anonymousId) q = q.eq("anonymous_id", anonymousId);
  else return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const { error } = await q;

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
  return NextResponse.json({ ok: true });
}
