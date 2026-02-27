-- Seed Walmart as external UCP partner for discovery aggregation.
-- Walmart UCP: https://www.walmart.com/.well-known/ucp
-- Discovery will query Walmart's UCP catalog in parallel with LocalDB when the endpoint is available.
-- To disable: UPDATE internal_agent_registry SET enabled = false WHERE base_url = 'https://www.walmart.com';

INSERT INTO internal_agent_registry (capability, base_url, display_name, enabled)
SELECT 'discovery', 'https://www.walmart.com', 'Walmart (UCP)', true
WHERE NOT EXISTS (
  SELECT 1 FROM internal_agent_registry
  WHERE base_url = 'https://www.walmart.com' AND capability = 'discovery'
);
