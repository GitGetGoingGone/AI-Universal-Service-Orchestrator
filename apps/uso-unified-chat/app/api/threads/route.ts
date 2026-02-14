import { NextResponse } from "next/server";
import { auth } from "@clerk/nextjs/server";
import { getSupabase } from "@/lib/supabase";

/**
 * GET /api/threads
 * List threads for signed-in user (user_id from Clerk) or anonymous (anonymous_id query param).
 * Returns [{ id, title, updated_at }] sorted by updated_at desc.
 */
export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const anonymousId = searchParams.get("anonymous_id");

  const supabase = getSupabase();
  if (!supabase) {
    return NextResponse.json(
      { error: "Persistence not configured" },
      { status: 503 }
    );
  }

  const { userId: clerkUserId } = await auth();

  if (clerkUserId) {
    const { data: user } = await supabase
      .from("users")
      .select("id")
      .eq("clerk_user_id", clerkUserId)
      .limit(1)
      .single();

    if (user?.id) {
      const { data: threads, error } = await supabase
        .from("chat_threads")
        .select("id, title, updated_at")
        .eq("user_id", user.id)
        .order("updated_at", { ascending: false })
        .limit(50);

      if (error) {
        return NextResponse.json({ error: error.message }, { status: 500 });
      }
      return NextResponse.json({
        threads: (threads ?? []).map((t) => ({
          id: t.id,
          title: t.title || "New chat",
          updated_at: t.updated_at,
        })),
      });
    }
  }

  if (anonymousId) {
    const { data: threads, error } = await supabase
      .from("chat_threads")
      .select("id, title, updated_at")
      .eq("anonymous_id", anonymousId)
      .order("updated_at", { ascending: false })
      .limit(50);

    if (error) {
      return NextResponse.json({ error: error.message }, { status: 500 });
    }
    return NextResponse.json({
      threads: (threads ?? []).map((t) => ({
        id: t.id,
        title: t.title || "New chat",
        updated_at: t.updated_at,
      })),
    });
  }

  return NextResponse.json({ threads: [] });
}
