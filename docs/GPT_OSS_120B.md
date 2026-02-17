# Configuring gpt-oss-120b (OpenRouter)

The orchestrator planner can use gpt-oss-120b or any OpenRouter model for agentic planning and composite experience design.

## Prerequisites

- Platform Admin access to the Partner Portal
- OpenRouter API key ([openrouter.ai](https://openrouter.ai))

## Configuration Steps

1. **Sign in** to the Partner Portal as a platform admin (user in `platform_admins`).

2. **Go to Platform → Config** and expand **LLM Providers**.

3. **Add an LLM provider**:
   - **Name**: e.g. "OpenRouter gpt-oss-120b"
   - **Provider type**: `openrouter`
   - **Endpoint**: `https://openrouter.ai/api/v1` (or leave blank; OpenRouter uses this by default)
   - **Model**: The OpenRouter model ID for gpt-oss-120b (e.g. check [OpenRouter models](https://openrouter.ai/docs#models) for the exact ID)
   - **API Key**: Your OpenRouter API key

4. **Set as active**: Click the provider to set it as the active LLM provider for the platform.

5. **Verify**: Send a chat request (e.g. "plan a date night"). The planner will use the configured model for tool selection and reasoning.

## Model ID

OpenRouter model IDs follow the format `provider/model-name`. For gpt-oss-120b, look up the current ID on [OpenRouter's models page](https://openrouter.ai/docs#models). Example: `openai/gpt-4o` for GPT-4o.

## Composite Experience Prompting

When using gpt-oss-120b (or any model) for composite experiences (date night, birthday party, etc.), the planner is instructed to:

- Prefer the **best combination** for the experience (e.g. flowers + dinner + movie for date night)
- Use engagement tools (weather, events, web search) when the user provides location/date
- Probe for details before fetching products when the request is generic

## Fallback

If the configured model fails or returns an error, the planner falls back to a rule-based plan (resolve_intent → discover_products/discover_composite).
