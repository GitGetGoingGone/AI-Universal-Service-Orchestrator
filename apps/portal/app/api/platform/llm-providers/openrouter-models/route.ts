import { NextResponse } from "next/server";
import { isPlatformAdmin } from "@/lib/auth";

const OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models";
const CACHE_MAX_AGE = 600;

let cached: { data: unknown[]; ts: number } | null = null;

export async function GET() {
  try {
    if (!(await isPlatformAdmin())) {
      return NextResponse.json({ detail: "Platform admin access required" }, { status: 403 });
    }

    const now = Date.now();
    if (cached && now - cached.ts < CACHE_MAX_AGE * 1000) {
      return NextResponse.json(cached, {
        headers: {
          "Cache-Control": `public, max-age=${CACHE_MAX_AGE}`,
        },
      });
    }

    const res = await fetch(OPENROUTER_MODELS_URL);
    if (!res.ok) {
      return NextResponse.json(
        { detail: `OpenRouter API error: ${res.status}` },
        { status: 502 }
      );
    }

    const json = (await res.json()) as { data?: unknown[] };
    const data = json.data ?? [];

    cached = { data, ts: now };

    return NextResponse.json(cached, {
      headers: {
        "Cache-Control": `public, max-age=${CACHE_MAX_AGE}`,
      },
    });
  } catch (err) {
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
