-- Internal Agent Registry: capability -> private partner/Business Agent base URLs.
-- Used only server-side by Scout; never exposed in APIs or manifests.

BEGIN;

CREATE TABLE IF NOT EXISTS internal_agent_registry (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  capability TEXT NOT NULL,
  base_url TEXT NOT NULL,
  display_name TEXT,
  enabled BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_internal_agent_registry_capability ON internal_agent_registry(capability);
CREATE INDEX IF NOT EXISTS idx_internal_agent_registry_enabled ON internal_agent_registry(enabled) WHERE enabled = true;

COMMENT ON TABLE internal_agent_registry IS 'Private registry: capability name to internal Business Agent base URL. Server-side only.';
COMMENT ON COLUMN internal_agent_registry.base_url IS 'Private URL; must not be exposed in any public response.';

COMMIT;
