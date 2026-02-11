import crypto from "crypto";
import { createSupabaseServerClient } from "./supabase";

/** Validate partner API key from Bearer or X-API-Key header. Returns partner_id or null. */
export async function getPartnerIdFromApiKey(request: Request): Promise<string | null> {
  const authHeader = request.headers.get("authorization");
  const apiKeyHeader = request.headers.get("x-api-key");
  const rawKey = authHeader?.startsWith("Bearer ")
    ? authHeader.slice(7).trim()
    : apiKeyHeader?.trim();

  if (!rawKey || !rawKey.startsWith("uso_")) return null;

  const secret =
    process.env.API_KEY_SECRET || process.env.SUPABASE_SECRET_KEY || "fallback-api-key-secret";
  const keyHash = crypto.createHmac("sha256", secret).update(rawKey).digest("hex");
  const keyPrefix = rawKey.slice(0, 12);

  const supabase = createSupabaseServerClient();
  const { data } = await supabase
    .from("partner_api_keys")
    .select("partner_id")
    .eq("key_prefix", keyPrefix)
    .eq("key_hash", keyHash)
    .eq("is_active", true)
    .single();

  if (!data) return null;

  await supabase
    .from("partner_api_keys")
    .update({ last_used_at: new Date().toISOString() })
    .eq("key_prefix", keyPrefix);

  return data.partner_id;
}
