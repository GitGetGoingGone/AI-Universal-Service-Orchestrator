import { auth, currentUser } from "@clerk/nextjs/server";
import { createSupabaseServerClient } from "./supabase";

export type PartnerStatus = "approved" | "pending" | null;

/** Returns true if the given Clerk user ID is a platform admin. */
export async function isPlatformAdminByUserId(userId: string | null): Promise<boolean> {
  if (!userId) return false;
  try {
    const supabase = createSupabaseServerClient();
    const { data } = await supabase
      .from("platform_admins")
      .select("id")
      .eq("clerk_user_id", userId)
      .limit(1)
      .single();
    return !!data;
  } catch {
    return false;
  }
}

/** Returns true if the current user is a platform admin. */
export async function isPlatformAdmin(): Promise<boolean> {
  const { userId } = await auth();
  return isPlatformAdminByUserId(userId);
}

export async function getPartnerId(): Promise<string | null> {
  const res = await getPartnerStatus();
  return res?.status === "approved" ? res.partnerId : null;
}

export async function getPartnerStatus(): Promise<{
  partnerId: string;
  status: "approved" | "pending";
} | null> {
  const { userId } = await auth();
  if (!userId) return null;

  const user = await currentUser();
  const emails = user?.emailAddresses?.map((e) => e.emailAddress).filter(Boolean) ?? [];
  if (emails.length === 0) return null;

  const supabase = createSupabaseServerClient();

  // Try approved first
  for (const email of emails) {
    const { data } = await supabase
      .from("partners")
      .select("id, verification_status")
      .eq("contact_email", email)
      .eq("is_active", true)
      .limit(1)
      .single();
    if (data) {
      const vs = data.verification_status;
      return {
        partnerId: data.id,
        status: vs === "approved" || vs === "verified" ? "approved" : "pending",
      };
    }
  }

  // Fallback: partner_members by email
  for (const email of emails) {
    const { data: pm } = await supabase
      .from("partner_members")
      .select("partner_id")
      .eq("email", email)
      .eq("is_active", true)
      .limit(1)
      .single();
    if (pm) {
      const { data: p } = await supabase
        .from("partners")
        .select("verification_status")
        .eq("id", pm.partner_id)
        .single();
      const vs = p?.verification_status;
      return {
        partnerId: pm.partner_id,
        status: vs === "approved" || vs === "verified" ? "approved" : "pending",
      };
    }
  }

  return null;
}
