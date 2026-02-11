import type { ImportSourceType, ImportSourceAdapter } from "../types";
import { shopifyCsvAdapter } from "./shopify-csv";

const adapters: Partial<Record<ImportSourceType, ImportSourceAdapter>> = {
  shopify_csv: shopifyCsvAdapter,
  // woocommerce_csv: add WooCommerce column mapping when needed
};

export function getImportAdapter(source: ImportSourceType): ImportSourceAdapter {
  const adapter = adapters[source];
  if (!adapter) {
    throw new Error(`Unknown import source: ${source}. Supported: shopify_csv`);
  }
  return adapter;
}

export { shopifyCsvAdapter } from "./shopify-csv";
