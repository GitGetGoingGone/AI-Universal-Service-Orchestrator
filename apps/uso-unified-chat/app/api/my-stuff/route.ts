import { NextResponse } from "next/server";
import { auth } from "@clerk/nextjs/server";
import { getSupabase } from "@/lib/supabase";

/**
 * GET /api/my-stuff
 * Returns favorites and standing intents for the current user.
 * Requires user_id (signed-in) or anonymous_id query param.
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

  const favorites: Array<{
    id: string;
    item_type: string;
    item_id: string;
    item_name: string | null;
    created_at: string;
  }> = [];
  const standingIntents: Array<{
    id: string;
    intent_description: string;
    status: string;
    created_at: string;
  }> = [];

  if (userId) {
    const { data: favs } = await supabase
      .from("user_favorites")
      .select("id, item_type, item_id, item_name, created_at")
      .eq("user_id", userId)
      .order("created_at", { ascending: false })
      .limit(50);
    if (favs) {
      favorites.push(
        ...favs.map((f) => ({
          id: f.id,
          item_type: f.item_type,
          item_id: f.item_id,
          item_name: f.item_name,
          created_at: f.created_at,
        }))
      );
    }

    const { data: intents } = await supabase
      .from("standing_intents")
      .select("id, intent_description, status, created_at")
      .eq("user_id", userId)
      .in("status", ["pending", "active"])
      .order("created_at", { ascending: false })
      .limit(20);
    if (intents) {
      standingIntents.push(
        ...intents.map((i) => ({
          id: i.id,
          intent_description: i.intent_description,
          status: i.status,
          created_at: i.created_at,
        }))
      );
    }
  } else if (anonymousId) {
    const { data: favs } = await supabase
      .from("user_favorites")
      .select("id, item_type, item_id, item_name, created_at")
      .eq("anonymous_id", anonymousId)
      .order("created_at", { ascending: false })
      .limit(50);
    if (favs) {
      favorites.push(
        ...favs.map((f) => ({
          id: f.id,
          item_type: f.item_type,
          item_id: f.item_id,
          item_name: f.item_name,
          created_at: f.created_at,
        }))
      );
    }
  }

  return NextResponse.json({
    favorites,
    standing_intents: standingIntents,
  });
}
