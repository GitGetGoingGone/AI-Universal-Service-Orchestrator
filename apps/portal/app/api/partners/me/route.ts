import { NextResponse } from "next/server";
import { auth } from "@clerk/nextjs/server";
import { getPartnerStatus } from "@/lib/auth";
import { createSupabaseServerClient } from "@/lib/supabase";

export async function GET() {
  const { userId } = await auth();
  if (!userId) {
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  }

  const status = await getPartnerStatus();
  if (!status) {
    return NextResponse.json({
      partner: null,
      message: "No partner account found. Use the same email as your registration, or contact support.",
    });
  }

  const supabase = createSupabaseServerClient();
  const { data: row } = await supabase
    .from("partners")
    .select(
      "id, business_name, seller_name, seller_url, return_policy_url, privacy_policy_url, terms_url, store_country, target_countries"
    )
    .eq("id", status.partnerId)
    .single();

  const partner = row
    ? {
        id: row.id,
        verification_status: status.status,
        business_name: row.business_name ?? undefined,
        seller_name: row.seller_name ?? undefined,
        seller_url: row.seller_url ?? undefined,
        return_policy_url: row.return_policy_url ?? undefined,
        privacy_policy_url: row.privacy_policy_url ?? undefined,
        terms_url: row.terms_url ?? undefined,
        store_country: row.store_country ?? undefined,
        target_countries: row.target_countries ?? undefined,
      }
    : { id: status.partnerId, verification_status: status.status };

  return NextResponse.json({
    partner,
    message: status.status === "pending"
      ? "Your application is pending approval."
      : undefined,
  });
}

/** Allowed seller/commerce profile fields for PATCH */
const PATCH_ALLOWED_KEYS = [
  "business_name",
  "seller_name",
  "seller_url",
  "return_policy_url",
  "privacy_policy_url",
  "terms_url",
  "store_country",
  "target_countries",
] as const;

export async function PATCH(request: Request) {
  const { userId } = await auth();
  if (!userId) {
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  }

  const partnerId = (await getPartnerStatus())?.partnerId;
  if (!partnerId) {
    return NextResponse.json({ detail: "No partner account" }, { status: 403 });
  }

  let body: Record<string, unknown>;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ detail: "Invalid JSON" }, { status: 400 });
  }

  const updates: Record<string, unknown> = {};
  for (const key of PATCH_ALLOWED_KEYS) {
    if (key in body && body[key] !== undefined) {
      updates[key] = body[key];
    }
  }
  if (Object.keys(updates).length === 0) {
    return NextResponse.json({ detail: "No allowed fields to update" }, { status: 400 });
  }

  const supabase = createSupabaseServerClient();
  const { error } = await supabase.from("partners").update(updates).eq("id", partnerId).select("id").single();
  if (error) {
    return NextResponse.json({ detail: error.message }, { status: 400 });
  }
  return NextResponse.json({ ok: true });
}
