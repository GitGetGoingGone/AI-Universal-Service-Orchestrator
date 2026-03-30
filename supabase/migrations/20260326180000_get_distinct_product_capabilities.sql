-- Distinct capability slugs from products.capabilities (JSONB array) for dynamic composite planning.

BEGIN;

CREATE OR REPLACE FUNCTION get_distinct_product_capabilities()
RETURNS TABLE(capability text)
LANGUAGE sql
STABLE
AS $$
  SELECT DISTINCT jsonb_array_elements_text(p.capabilities) AS capability
  FROM products p
  WHERE p.deleted_at IS NULL
    AND p.capabilities IS NOT NULL
    AND jsonb_typeof(p.capabilities) = 'array'
    AND jsonb_array_length(p.capabilities) > 0
  ORDER BY capability;
$$;

COMMENT ON FUNCTION get_distinct_product_capabilities IS 'Returns distinct capabilities from products for catalog-driven intent / composite planning';

COMMIT;
