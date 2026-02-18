import { NextResponse } from "next/server";
import { auth } from "@clerk/nextjs/server";
import { getSupabase } from "@/lib/supabase";

/**
 * POST /api/my-stuff/favorites
 * Add a favorite. Requires sign-in. Body: { item_type?, item_id, item_name? }
 */
export async function POST(req: Request) {
  try {
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
    } = body as {
      item_type?: string;
      item_id?: string;
      item_name?: string;
    };

    if (!item_id) {
      return NextResponse.json({ error: "item_id required" }, { status: 400 });
    }

    let userId: string | null = null;
    let clerkUserId: string | null = null;
    try {
      const authResult = await auth();
      clerkUserId = authResult?.userId ?? null;
    } catch (authErr) {
      console.warn("[favorites] Clerk auth failed:", authErr);
      clerkUserId = null;
    }

    if (!clerkUserId) {
      return NextResponse.json(
        { error: "Sign in to save favorites" },
        { status: 401 }
      );
    }

    // Resolve or create user in Supabase
    const { data: user, error: selectError } = await supabase
      .from("users")
      .select("id")
      .eq("clerk_user_id", clerkUserId)
      .limit(1)
      .single();

    if (selectError && selectError.code !== "PGRST116") {
      console.error("[favorites] Supabase users select failed:", selectError);
      return NextResponse.json(
        { error: "Unable to save favorites. Database temporarily unavailable." },
        { status: 503 }
      );
    }
    userId = user?.id ?? null;

    if (!userId) {
      const { data: created, error: insertError } = await supabase
        .from("users")
        .insert({ id: crypto.randomUUID(), clerk_user_id: clerkUserId })
        .select("id")
        .single();

      if (insertError) {
        if (insertError.code === "23505") {
          // Race: user was created by another request; retry select
          const { data: retry } = await supabase
            .from("users")
            .select("id")
            .eq("clerk_user_id", clerkUserId)
            .limit(1)
            .single();
          userId = retry?.id ?? null;
        }
        if (!userId) {
          console.error("[favorites] Supabase users insert failed:", insertError);
          return NextResponse.json(
            { error: "Unable to save favorites. Database temporarily unavailable." },
            { status: 503 }
          );
        }
      } else {
        userId = created?.id ?? null;
      }
    }

    if (!userId) {
      return NextResponse.json(
        { error: "Sign in to save favorites" },
        { status: 401 }
      );
    }

    const row: Record<string, unknown> = {
      item_type,
      item_id: String(item_id),
      item_name: item_name || null,
      item_metadata: {},
      user_id: userId,
    };

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
  } catch (err) {
    const msg = err instanceof Error ? err.message : "Failed to save favorite";
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
