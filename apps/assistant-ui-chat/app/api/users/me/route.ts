import { NextResponse } from "next/server";
import { auth } from "@clerk/nextjs/server";
import { getSupabase } from "@/lib/supabase";

export async function GET() {
  const { userId: clerkUserId } = await auth();
  if (!clerkUserId) {
    return NextResponse.json({ user_id: null });
  }

  const supabase = getSupabase();
  if (!supabase) {
    return NextResponse.json({ user_id: null });
  }

  const { data: existing } = await supabase
    .from("users")
    .select("id")
    .eq("clerk_user_id", clerkUserId)
    .limit(1)
    .single();

  if (existing) {
    return NextResponse.json({ user_id: existing.id });
  }

  const { data: created } = await supabase
    .from("users")
    .insert({
      id: crypto.randomUUID(),
      clerk_user_id: clerkUserId,
    })
    .select("id")
    .single();

  if (!created) {
    return NextResponse.json({ user_id: null });
  }
  return NextResponse.json({ user_id: created.id });
}
