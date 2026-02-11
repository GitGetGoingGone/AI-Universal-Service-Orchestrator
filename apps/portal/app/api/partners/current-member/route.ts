import { NextResponse } from "next/server";
import { currentUser } from "@clerk/nextjs/server";
import { getPartnerId } from "@/lib/auth";
import { createSupabaseServerClient } from "@/lib/supabase";

export async function GET() {
  const partnerId = await getPartnerId();
  if (!partnerId) {
    return NextResponse.json({ detail: "No partner account" }, { status: 403 });
  }

  const user = await currentUser();
  const emails = user?.emailAddresses?.map((e) => e.emailAddress).filter(Boolean) ?? [];

  const supabase = createSupabaseServerClient();
  for (const email of emails) {
    const { data } = await supabase
      .from("partner_members")
      .select("id")
      .eq("partner_id", partnerId)
      .eq("email", email)
      .eq("is_active", true)
      .single();
    if (data) {
      return NextResponse.json({ memberId: data.id });
    }
  }

  return NextResponse.json({ memberId: null });
}
