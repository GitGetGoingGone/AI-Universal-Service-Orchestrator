import { NextResponse } from "next/server";
import { getSupabase } from "@/lib/supabase";

const ORCHESTRATOR_URL =
  process.env.ORCHESTRATOR_URL || "http://localhost:8002";

async function getUserIdByPhone(
  supabase: ReturnType<typeof getSupabase>,
  phone: string
): Promise<string | null> {
  if (!supabase) return null;
  return supabase
    .from("account_links")
    .select("user_id")
    .eq("platform", "whatsapp")
    .eq("platform_user_id", phone)
    .eq("is_active", true)
    .limit(1)
    .single()
    .then((r) => r.data?.user_id ?? null);
}

async function getOrCreateThreadForUser(
  supabase: ReturnType<typeof getSupabase>,
  userId: string,
  title: string
) {
  if (!supabase) return null;
  const { data: existing } = await supabase
    .from("chat_threads")
    .select("id")
    .eq("user_id", userId)
    .order("updated_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  if (existing?.id) return existing.id;

  const { data: created } = await supabase
    .from("chat_threads")
    .insert({
      user_id: userId,
      title: title.slice(0, 100) || "WhatsApp chat",
    })
    .select("id")
    .single();

  return created?.id ?? null;
}

export async function POST(req: Request) {
  const supabase = getSupabase();
  const formData = await req.formData().catch(() => null);
  const rawFrom = formData?.get("From")?.toString() ?? "";
  const from = rawFrom.replace(/^whatsapp:/i, "").trim();
  const body = formData?.get("Body")?.toString()?.trim() ?? "";

  if (!from || !body) {
    return new NextResponse(
      '<?xml version="1.0" encoding="UTF-8"?><Response><Message>Invalid request.</Message></Response>',
      { headers: { "Content-Type": "text/xml" } }
    );
  }

  const userId = await getUserIdByPhone(supabase, from);
  if (!userId) {
    return new NextResponse(
      `<?xml version="1.0" encoding="UTF-8"?><Response><Message>Please sign in at the web app and connect your WhatsApp to use discovery. Visit the app, sign in, and go to Settings → Connect WhatsApp.</Message></Response>`,
      { headers: { "Content-Type": "text/xml" } }
    );
  }

  let threadId: string | null = null;
  if (supabase) {
    threadId = await getOrCreateThreadForUser(supabase, userId, body);
    if (threadId) {
      await supabase.from("chat_messages").insert({
        thread_id: threadId,
        role: "user",
        content: body,
        channel: "whatsapp",
      });
    }
  }

  try {
    const res = await fetch(`${ORCHESTRATOR_URL}/api/v1/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: body,
        limit: 20,
        platform: "whatsapp",
        thread_id: from,
        platform_user_id: from,
        user_id: userId,
      }),
    });

    const data = await res.json().catch(() => ({}));
    const summary = data.summary ?? data.message ?? "I couldn't process that. Try the web app for full experience.";
    const text = String(summary).slice(0, 1600);

    if (supabase && threadId) {
      await supabase.from("chat_messages").insert({
        thread_id: threadId,
        role: "assistant",
        content: text,
        channel: "whatsapp",
      });
    }

    return new NextResponse(
      `<?xml version="1.0" encoding="UTF-8"?><Response><Message>${escapeXml(text)}</Message></Response>`,
      { headers: { "Content-Type": "text/xml" } }
    );
  } catch (err) {
    const msg = err instanceof Error ? err.message : "Error";
    return new NextResponse(
      `<?xml version="1.0" encoding="UTF-8"?><Response><Message>Sorry, something went wrong. Try again later.</Message></Response>`,
      { headers: { "Content-Type": "text/xml" } }
    );
  }
}

function escapeXml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}
