/**
 * Normalized product shape used by all import sources.
 * Maps to our products table + optional initial inventory.
 */
export type NormalizedProduct = {
  name: string;
  description?: string | null;
  price: number;
  currency?: string;
  product_type?: "product" | "service";
  unit?: string;
  url?: string | null;
  brand?: string | null;
  image_url?: string | null;
  is_available?: boolean;
  is_eligible_search?: boolean;
  is_eligible_checkout?: boolean;
  availability?: string;
  target_countries?: string[] | null;
  /** If set, create/update product_inventory with this quantity after product insert */
  initial_quantity?: number | null;
};

/** Supported import sources; extend for Shopify API, WooCommerce, etc. */
export type ImportSourceType = "shopify_csv" | "woocommerce_csv"; // add more as needed

export type ImportSourceAdapter = (
  row: Record<string, string>
) => NormalizedProduct | null;
