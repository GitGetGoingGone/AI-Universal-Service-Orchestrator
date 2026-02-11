import type { NormalizedProduct } from "../types";

/**
 * Shopify product export column set.
 * Maps Shopify CSV columns to our normalized product shape.
 * See: https://help.shopify.com/en/manual/products/import-export/export-products
 */
export function shopifyCsvAdapter(row: Record<string, string>): NormalizedProduct | null {
  const title = row["Title"]?.trim();
  const variantPrice = row["Variant Price"]?.trim();
  if (!title || variantPrice === undefined || variantPrice === "") {
    return null;
  }

  const price = parseFloat(variantPrice);
  if (Number.isNaN(price) || price < 0) {
    return null;
  }

  const body = row["Body (HTML)"]?.trim() ?? "";
  const vendor = row["Vendor"]?.trim() || null;
  const type = (row["Type"]?.trim() ?? "").toLowerCase();
  const published = row["Published"]?.trim().toLowerCase();
  const imageSrc = row["Image Src"]?.trim() || null;
  const status = (row["Status"]?.trim() ?? "").toLowerCase();

  const isService =
    type === "service" ||
    type === "services" ||
    type === "rental" ||
    type === "bookable";
  const is_available =
    published === "true" ||
    published === "1" ||
    published === "yes" ||
    status === "active";

  let initial_quantity: number | null = null;
  const qtyStr = row["Variant Inventory Qty"]?.trim();
  if (qtyStr !== "" && qtyStr !== undefined) {
    const q = parseInt(qtyStr, 10);
    if (!Number.isNaN(q) && q >= 0) initial_quantity = q;
  }

  return {
    name: title,
    description: body || null,
    price,
    currency: "USD",
    product_type: isService ? "service" : "product",
    unit: isService ? "hour" : "piece",
    brand: vendor,
    image_url: imageSrc,
    is_available,
    is_eligible_search: true,
    is_eligible_checkout: false,
    availability: is_available ? "in_stock" : "out_of_stock",
    initial_quantity,
  };
}
