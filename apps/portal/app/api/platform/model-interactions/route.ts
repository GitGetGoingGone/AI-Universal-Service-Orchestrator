import { NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/lib/supabase";
import { isPlatformAdmin } from "@/lib/auth";

export async function GET() {
  try {
    if (!(await isPlatformAdmin())) {
      return NextResponse.json({ detail: "Platform admin access required" }, { status: 403 });
    }

    const supabase = createSupabaseServerClient();
    const { data, error } = await supabase
      .from("model_interaction_prompts")
      .select("id, interaction_type, display_name, when_used, system_prompt, enabled, max_tokens, display_order")
      .order("display_order", { ascending: true })
      .order("interaction_type", { ascending: true });

    if (error) {
      return NextResponse.json({ detail: error.message }, { status: 500 });
    }

    return NextResponse.json(data ?? []);
  } catch (err) {
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}

export async function PATCH(request: Request) {
  try {
    if (!(await isPlatformAdmin())) {
      return NextResponse.json({ detail: "Platform admin access required" }, { status: 403 });
    }

    const body = await request.json();
    const updates = Array.isArray(body.updates) ? body.updates : [body];

    if (updates.length === 0) {
      return NextResponse.json({ detail: "No updates provided" }, { status: 400 });
    }

    const supabase = createSupabaseServerClient();
    const results: unknown[] = [];

    for (const u of updates) {
      const interaction_type = u.interaction_type;
      if (!interaction_type) {
        return NextResponse.json({ detail: "interaction_type required for each update" }, { status: 400 });
      }

      const patch: Record<string, unknown> = { updated_at: new Date().toISOString() };
      if (u.system_prompt !== undefined) patch.system_prompt = u.system_prompt;
      if (u.enabled !== undefined) patch.enabled = Boolean(u.enabled);
      if (u.max_tokens !== undefined) {
        const n = Number(u.max_tokens);
        patch.max_tokens = Number.isFinite(n) ? Math.max(50, Math.min(4000, n)) : 500;
      }

      const { data, error } = await supabase
        .from("model_interaction_prompts")
        .update(patch)
        .eq("interaction_type", interaction_type)
        .select()
        .single();

      if (error) {
        return NextResponse.json({ detail: error.message }, { status: 500 });
      }
      results.push(data);
    }

    return NextResponse.json(results);
  } catch (err) {
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
