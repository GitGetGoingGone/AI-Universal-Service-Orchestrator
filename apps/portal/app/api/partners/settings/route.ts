import { NextResponse } from "next/server";
import { getPartnerId } from "@/lib/auth";
import { createSupabaseServerClient } from "@/lib/supabase";

export async function GET() {
  const partnerId = await getPartnerId();
  if (!partnerId) {
    return NextResponse.json({ detail: "No partner account" }, { status: 403 });
  }

  const supabase = createSupabaseServerClient();
  const { data: partner } = await supabase
    .from("partners")
    .select("is_accepting_orders, capacity_limit, ai_auto_respond_enabled")
    .eq("id", partnerId)
    .single();

  const { data: notifPrefs } = await supabase
    .from("notification_preferences")
    .select("type, email_enabled, push_enabled, in_app_enabled")
    .eq("partner_id", partnerId);

  const prefs = (notifPrefs ?? []).reduce(
    (acc, p) => {
      acc[p.type] = {
        email_enabled: p.email_enabled,
        push_enabled: p.push_enabled,
        in_app_enabled: p.in_app_enabled,
      };
      return acc;
    },
    {} as Record<string, { email_enabled: boolean; push_enabled: boolean; in_app_enabled: boolean }>
  );

  return NextResponse.json({
    isAcceptingOrders: partner?.is_accepting_orders ?? true,
    capacityLimit: partner?.capacity_limit ?? null,
    aiAutoRespondEnabled: partner?.ai_auto_respond_enabled ?? false,
    notificationPreferences: prefs,
  });
}

export async function PATCH(request: Request) {
  const partnerId = await getPartnerId();
  if (!partnerId) {
    return NextResponse.json({ detail: "No partner account" }, { status: 403 });
  }

  const body = await request.json();
  const isAcceptingOrders = body?.is_accepting_orders as boolean | undefined;
  const capacityLimit = body?.capacity_limit as number | null | undefined;
  const aiAutoRespondEnabled = body?.ai_auto_respond_enabled as boolean | undefined;

  const updates: Record<string, unknown> = {};
  if (isAcceptingOrders !== undefined) updates.is_accepting_orders = isAcceptingOrders;
  if (capacityLimit !== undefined) updates.capacity_limit = capacityLimit;
  if (aiAutoRespondEnabled !== undefined) updates.ai_auto_respond_enabled = aiAutoRespondEnabled;

  if (Object.keys(updates).length === 0) {
    return NextResponse.json({ detail: "No updates" }, { status: 400 });
  }

  const supabase = createSupabaseServerClient();
  const { data, error } = await supabase
    .from("partners")
    .update(updates)
    .eq("id", partnerId)
    .select()
    .single();

  if (error) return NextResponse.json({ detail: error.message }, { status: 500 });
  return NextResponse.json(data);
}
