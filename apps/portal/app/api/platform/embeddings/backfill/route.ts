import { NextRequest, NextResponse } from "next/server";
import { isPlatformAdmin } from "@/lib/auth";

const DISCOVERY_SERVICE_URL =
  process.env.DISCOVERY_SERVICE_URL ?? process.env.NEXT_PUBLIC_DISCOVERY_SERVICE_URL ?? "";

export async function POST(request: NextRequest) {
  if (!(await isPlatformAdmin())) {
    return NextResponse.json({ detail: "Platform admin access required" }, { status: 403 });
  }

  if (!DISCOVERY_SERVICE_URL) {
    return NextResponse.json(
      { detail: "Discovery service URL not configured (DISCOVERY_SERVICE_URL)" },
      { status: 503 }
    );
  }

  const { searchParams } = new URL(request.url);
  const type = searchParams.get("type") ?? "products";
  const limit = searchParams.get("limit") ?? "500";
  const productId = searchParams.get("product_id") ?? "";
  const articleId = searchParams.get("article_id") ?? "";

  const params = new URLSearchParams();
  params.set("type", type);
  if (type === "products" && productId) params.set("product_id", productId);
  if (type === "kb_articles" && articleId) params.set("article_id", articleId);
  if (!productId && !articleId) params.set("limit", limit);

  const base = DISCOVERY_SERVICE_URL.replace(/\/$/, "");
  try {
    const res = await fetch(`${base}/api/v1/admin/embeddings/backfill?${params.toString()}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      return NextResponse.json(data || { detail: "Backfill failed" }, { status: res.status });
    }
    return NextResponse.json(data);
  } catch (err) {
    return NextResponse.json(
      { detail: err instanceof Error ? err.message : "Failed to reach Discovery service" },
      { status: 502 }
    );
  }
}
