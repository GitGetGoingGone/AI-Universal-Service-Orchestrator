import { NextResponse } from "next/server";
import { auth } from "@clerk/nextjs/server";
import { getSupabase } from "@/lib/supabase";

/**
 * POST /api/threads/[id]/link
 * Link an anonymous thread to the signed-in user (save conversation after login).
 * Body: { anonymous_id: string } - must match current thread's anonymous_id.
 */
export async function POST(
  req: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const clerkUserId = await auth().then((a) => a.userId);
  if (!clerkUserId) {
    return NextResponse.json({ error: "Sign in required" }, { status: 401 });
  }

  const supabase = getSupabase();
  if (!supabase) {
    return NextResponse.json(
      { error: "Persistence not configured" },
      { status: 503 }
    );
  }

  const body = await req.json().catch(() => ({}));
  const anonymousId = typeof body.anonymous_id === "string" ? body.anonymous_id.trim() : "";

  if (!anonymousId) {
    return NextResponse.json(
      { error: "anonymous_id required" },
      { status: 400 }
    );
  }

  const { data: user } = await supabase
    .from("users")
    .select("id")
    .eq("clerk_user_id", clerkUserId)
    .limit(1)
    .single();

  if (!user?.id) {
    return NextResponse.json({ error: "User not found" }, { status: 404 });
  }

  const { data: thread, error: threadError } = await supabase
    .from("chat_threads")
    .select("id, anonymous_id, user_id")
    .eq("id", id)
    .single();

  if (threadError || !thread) {
    return NextResponse.json({ error: "Thread not found" }, { status: 404 });
  }

  if (thread.user_id) {
    return NextResponse.json({ ok: true, message: "Already linked" });
  }

  if (thread.anonymous_id !== anonymousId) {
    return NextResponse.json(
      { error: "Thread access denied" },
      { status: 403 }
    );
  }

  const { error: updateError } = await supabase
    .from("chat_threads")
    .update({
      user_id: user.id,
      anonymous_id: null,
      updated_at: new Date().toISOString(),
    })
    .eq("id", id);

  if (updateError) {
    return NextResponse.json(
      { error: updateError.message },
      { status: 500 }
    );
  }

  return NextResponse.json({ ok: true });
}
