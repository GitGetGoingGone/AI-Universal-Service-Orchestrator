# Configuring gpt-oss-120b for the Orchestrator

The orchestrator planner and engagement response use the LLM configured in Platform Config. You can use **gpt-oss-120b** (OpenAI's open-weight 117B MoE model) via OpenRouter.

## Prerequisites

- OpenRouter API key from [openrouter.ai](https://openrouter.ai)
- Platform Admin access to the Partner Portal

## Configuration Steps

1. **Open Platform Config**  
   Sign in as a platform admin → **Platform** → **Config**.

2. **Add LLM Provider**  
   In the **LLM Providers** section:
   - **Name**: e.g. "gpt-oss-120b (OpenRouter)"
   - **Provider type**: `openrouter`
   - **API Key**: Your OpenRouter API key
   - **Model**: `openai/gpt-oss-120b`

3. **Set as Active**  
   Click **Use for planner** (or equivalent) to set this provider as the active LLM for the orchestrator.

4. **Verify**  
   Send a chat request (e.g. "plan a date night"). The planner and engagement response will use gpt-oss-120b.

## Model ID

On OpenRouter, the model ID is:

```
openai/gpt-oss-120b
```

Use this exact string in the **Model** field when adding the LLM provider.

## Custom Endpoint (Alternative)

If you host gpt-oss-120b on your own infrastructure:

1. Add an LLM provider with **Provider type**: `custom`
2. **Endpoint**: Your API base URL (e.g. `https://your-llm.example.com/v1`)
3. **API Key**: Your service key (if required)
4. **Model**: The model name your API expects (e.g. `gpt-oss-120b`)

## Composite Experience Behavior

When using gpt-oss-120b for composite experiences (e.g. date night), the planner is instructed to prefer the **best combination** for the experience (flowers + dinner + movie). The engagement response will incorporate product data and any engagement context (weather, events, web search) when those external APIs are configured.
