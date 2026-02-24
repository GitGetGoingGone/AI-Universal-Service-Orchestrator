import { NextResponse } from "next/server";
import { isPlatformAdmin } from "@/lib/auth";

const DISCOVERY_SERVICE_URL =
  process.env.DISCOVERY_SERVICE_URL ?? process.env.NEXT_PUBLIC_DISCOVERY_SERVICE_URL ?? "";

export async function GET() {
  if (!(await isPlatformAdmin())) {
    return NextResponse.json({ detail: "Platform admin access required" }, { status: 403 });
  }

  if (!DISCOVERY_SERVICE_URL) {
    return NextResponse.json(
      {
        embedding_configured: false,
        products: { total: 0, with_embedding: 0, without_embedding: 0 },
        kb_articles: { total: 0, with_embedding: 0, without_embedding: 0 },
        error: "Discovery service URL not configured (DISCOVERY_SERVICE_URL)",
      },
      { status: 200 }
    );
  }

  const base = DISCOVERY_SERVICE_URL.replace(/\/$/, "");
  try {
    const res = await fetch(`${base}/api/v1/admin/embeddings/status`, { cache: "no-store" });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      return NextResponse.json(data || { detail: "Discovery service error" }, { status: res.status });
    }
    return NextResponse.json(data);
  } catch (err) {
    return NextResponse.json(
      {
        embedding_configured: false,
        products: { total: 0, with_embedding: 0, without_embedding: 0 },
        kb_articles: { total: 0, with_embedding: 0, without_embedding: 0 },
        error: err instanceof Error ? err.message : "Failed to reach Discovery service",
      },
      { status: 200 }
    );
  }
}
