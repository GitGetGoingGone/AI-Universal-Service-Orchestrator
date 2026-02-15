-- Migration: Add customer_phone to orders for contact capture before payment
-- Date: 2025-01-28

BEGIN;

ALTER TABLE orders ADD COLUMN IF NOT EXISTS customer_phone TEXT;

COMMENT ON COLUMN orders.customer_phone IS 'Phone number collected before payment for order contact (anonymous users)';

COMMIT;
