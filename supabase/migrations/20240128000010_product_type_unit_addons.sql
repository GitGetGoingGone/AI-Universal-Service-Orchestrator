-- Add product_type (product/service) and unit (hour, piece, etc.) for adaptive product/service catalog
ALTER TABLE products ADD COLUMN IF NOT EXISTS product_type VARCHAR(20) DEFAULT 'product';
ALTER TABLE products ADD COLUMN IF NOT EXISTS unit VARCHAR(20) DEFAULT 'piece';

COMMENT ON COLUMN products.product_type IS 'product or service';
COMMENT ON COLUMN products.unit IS 'hour, piece, day, session, etc.';
