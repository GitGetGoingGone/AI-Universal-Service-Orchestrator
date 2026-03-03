# LLM config, server URL, and API key testing

## Where each service gets its LLM config

| Consumer | Config source | Code location |
|----------|---------------|---------------|
| **Intent service** | Supabase `platform_config` + `llm_providers` (via `get_platform_llm_config`) when it calls the LLM. Intent can also use **heuristics** (no LLM), so intent can “work” even when the LLM key would 401. | Intent service uses its own `llm` module; when it uses the platform LLM it goes through shared `get_platform_llm_config` + `get_llm_chat_client`. |
| **Orchestrator (Planner, engagement, etc.)** | `get_llm_config()` in **orchestrator** `api/admin.py` → Supabase `platform_config` and `llm_providers` row for `active_llm_provider_id`. Returns `provider`, `model`, `temperature`, `endpoint`, `api_key` (decrypted). | `services/orchestrator-service/api/admin.py` → `get_llm_config()`. Planner/engagement use this and then `get_llm_chat_client(llm_config)` from `packages/shared/platform_llm.py`. |

So:

- **Intent** can work because it sometimes uses **heuristics** (no API call), or because it uses the same DB config and a **different code path** (e.g. different `endpoint` handling).
- **Planner** always uses the LLM. It uses **orchestrator’s** `get_llm_config()` and then `get_llm_chat_client()`. If the key or endpoint is wrong for that path, you get 401.

A 401 with “Incorrect API key” usually means:

- The **same** key is being sent to a **different** base URL than the one it was issued for (e.g. Azure key sent to `api.openai.com`, or OpenAI key sent to an Azure endpoint), or
- The key in the DB is wrong/expired for the URL you’re actually calling.

## Server URL and model

- **OpenAI (direct)**  
  - **URL:** `https://api.openai.com/v1` (OpenAI SDK default when you use `OpenAI(api_key=...)` with no `base_url`).  
  - **Model:** From config; default in code is `gpt-4o`.  
  - Used when `llm_providers.endpoint` is **not** set and provider is `openai`/`azure`.

- **Azure OpenAI**  
  - **URL:** The value of `llm_providers.endpoint` (e.g. `https://your-resource.openai.azure.com`).  
  - **Model:** From config (e.g. `gpt-4o` or your deployment name).  
  - Used when `llm_providers.endpoint` **is** set; client is `AzureOpenAI(azure_endpoint=..., api_key=...)`.

So: **server URL** = either `https://api.openai.com/v1` (OpenAI) or your Azure endpoint from DB. **Model** = from config, typically `gpt-4o`.

## How to test if the API key is working

### 1. Use the orchestrator test-interaction endpoint (same path as planner)

This uses the **same** `get_llm_config()` and LLM client as the planner:

```bash
curl -X POST "http://localhost:8002/api/v1/admin/test-interaction" \
  -H "Content-Type: application/json" \
  -d '{"interaction_type": "planner", "sample_user_message": "What is the next action?"}'
```

- **200 + response body** → key and config work for the planner path.
- **401** → key or endpoint is wrong for the URL being called (check `llm_providers.endpoint` and key type).
- **503 "No LLM configured or API key missing"** → `get_llm_config()` returned no `api_key` (e.g. no `active_llm_provider_id` or decryption failed).

### 2. Test OpenAI key directly (if you use OpenAI, not Azure)

Replace `YOUR_OPENAI_API_KEY` with your key:

```bash
curl https://api.openai.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_OPENAI_API_KEY" \
  -d '{
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "Say hello"}],
    "max_tokens": 50
  }'
```

- **200** → key is valid for `https://api.openai.com/v1` and `gpt-4o`.
- **401** → key is invalid for OpenAI (wrong key, or it’s an Azure key).

### 3. Check what config the orchestrator is using

Inspect `platform_config` and the active `llm_providers` row (e.g. in Supabase):

- `platform_config.active_llm_provider_id` → which row is used.
- That row’s `provider_type`, `endpoint`, `model`, and `api_key_encrypted` (and decryption) determine URL and key.

If **intent works** but **planner returns 401**, compare:

- Whether Intent is using the same `llm_providers` row and the same `endpoint` (Azure vs OpenAI).
- Whether the planner path is getting `endpoint` and `api_key` correctly from `get_llm_config()` (e.g. log or debug the returned `llm_config` when the planner runs).

Summary:

- **Server URL:** `https://api.openai.com/v1` for OpenAI; otherwise `llm_providers.endpoint` for Azure.
- **Model:** From config, default `gpt-4o`.
- **Test key:** Use `POST /api/v1/admin/test-interaction` with `interaction_type: "planner"` and/or the `curl` to `api.openai.com` above.
