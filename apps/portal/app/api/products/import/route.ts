import { NextResponse } from "next/server";
import { getPartnerId } from "@/lib/auth";
import { createSupabaseServerClient } from "@/lib/supabase";
import { parseCSV } from "@/lib/import/parse-csv";
import { getImportAdapter } from "@/lib/import/adapters";
import type { ImportSourceType, NormalizedProduct } from "@/lib/import/types";

const MAX_FILE_SIZE = 2 * 1024 * 1024; // 2MB
const MAX_ROWS = 500;

export async function POST(request: Request) {
  const partnerId = await getPartnerId();
  if (!partnerId) {
    return NextResponse.json({ detail: "No partner account" }, { status: 403 });
  }

  let formData: FormData;
  try {
    formData = await request.formData();
  } catch {
    return NextResponse.json({ detail: "Invalid form data" }, { status: 400 });
  }

  const file = formData.get("file") as File | null;
  const source = (formData.get("source") as string)?.trim() as ImportSourceType | undefined;

  if (!file || !source) {
    return NextResponse.json(
      { detail: "Missing 'file' or 'source'. Use source: shopify_csv" },
      { status: 400 }
    );
  }

  if (file.size > MAX_FILE_SIZE) {
    return NextResponse.json(
      { detail: `File too large. Max ${MAX_FILE_SIZE / 1024 / 1024}MB` },
      { status: 400 }
    );
  }

  let text: string;
  try {
    text = await file.text();
  } catch {
    return NextResponse.json({ detail: "Failed to read file" }, { status: 400 });
  }

  const { headers, rows } = parseCSV(text);
  if (rows.length === 0) {
    return NextResponse.json(
      { detail: "CSV has no data rows (only header or empty)" },
      { status: 400 }
    );
  }
  if (rows.length > MAX_ROWS) {
    return NextResponse.json(
      { detail: `Too many rows. Max ${MAX_ROWS}` },
      { status: 400 }
    );
  }

  let adapter: (row: Record<string, string>) => NormalizedProduct | null;
  try {
    adapter = getImportAdapter(source);
  } catch (e) {
    return NextResponse.json(
      { detail: e instanceof Error ? e.message : "Unknown source" },
      { status: 400 }
    );
  }

  const normalized: (NormalizedProduct & { _rowIndex: number })[] = [];
  for (let i = 0; i < rows.length; i++) {
    const product = adapter(rows[i]);
    if (product) {
      normalized.push({ ...product, _rowIndex: i + 2 });
    }
  }

  const supabase = createSupabaseServerClient();
  const created: string[] = [];
  const errors: { row: number; message: string }[] = [];

  for (const p of normalized) {
    const { _rowIndex, initial_quantity, ...rest } = p;
    const rowIndex = _rowIndex;

    const insert: Record<string, unknown> = {
      partner_id: partnerId,
      name: rest.name,
      description: rest.description ?? null,
      price: Number(rest.price),
      currency: rest.currency ?? "USD",
      product_type: rest.product_type === "service" ? "service" : "product",
      unit: rest.unit ?? "piece",
      url: rest.url ?? null,
      brand: rest.brand ?? null,
      image_url: rest.image_url ?? null,
      is_available: rest.is_available !== false,
      is_eligible_search: rest.is_eligible_search !== false,
      is_eligible_checkout: !!rest.is_eligible_checkout,
      availability: rest.availability ?? "in_stock",
      target_countries: rest.target_countries ?? null,
    };

    const { data, error } = await supabase
      .from("products")
      .insert(insert)
      .select("id")
      .single();

    if (error) {
      errors.push({ row: rowIndex, message: error.message });
      continue;
    }

    if (data?.id) {
      created.push(data.id);
      if (initial_quantity != null && initial_quantity >= 0) {
        await supabase
          .from("product_inventory")
          .upsert(
            {
              product_id: data.id,
              quantity: initial_quantity,
              low_stock_threshold: 5,
              auto_unlist_when_zero: true,
              updated_at: new Date().toISOString(),
            },
            { onConflict: "product_id" }
          );
      }
    }
  }

  return NextResponse.json({
    created: created.length,
    failed: errors.length,
    skipped: rows.length - normalized.length,
    errors: errors.slice(0, 20),
    total_rows: rows.length,
  });
}
