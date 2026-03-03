# Forcing Model-Based Intent for ChatGPT

To ensure all probing data (date, budget, preferences, location) are captured when users interact via ChatGPT or Gemini, follow these steps.

## 1. Pass Conversation History (`messages`)

**Critical**: The chat API must receive `messages` so the orchestrator can derive `last_suggestion` (the last assistant message). Without it, answers like "any day next week" are misclassified as product searches.

### ChatGPT Custom GPT Instructions

Add this to your Custom GPT's **Instructions**:

```
When calling the chat action (POST /api/v1/chat), ALWAYS include the messages parameter with the last 4-6 messages from this conversation. Format:
messages: [
  { "role": "user", "content": "plan a date night" },
  { "role": "assistant", "content": "What date? Budget? Preferences? Location?" },
  { "role": "user", "content": "any day next week" }
]

This ensures the platform correctly interprets follow-up answers (date, budget, preferences) in context.
```

### OpenAPI Schema

The schema in `docs/openapi-chatgpt-actions.yaml` already includes `messages` in the chat request body. Re-import the schema after updates.

## 2. Enable Force Model-Based Intent (Admin)

1. Go to **Platform Config** → **LLM & AI**
2. Check **Force model-based intent (ChatGPT/Gemini)**
3. Save

When enabled:
- Intent resolution uses the LLM only (no heuristic fallback)
- If the LLM fails or is unavailable, the request fails (no silent fallback to heuristics)
- Ensures probing answers are always interpreted by the model

**Prerequisites**:
- LLM provider configured with valid API key
- Intent prompt enabled in Model Interactions
- ChatGPT/Gemini sending `messages` (see step 1)

## 3. Model Interaction Prompts

The **Intent** prompt in Model Interactions includes rules for probing answers. If you use a custom intent prompt, ensure it contains:

> When last_suggestion contains probing questions (e.g. "What date? Budget? Preferences? Location?") and the user answers (e.g. "any day next week", "this weekend", "whatever", "$100"): stay in discover_composite context. Use experience_name from the conversation. Do NOT use the user's answer as search_query—search_query is for product terms only.

The default intent prompt (from migration) already includes this rule.

## Summary Checklist

| Step | Action |
|------|--------|
| 1 | Add GPT instructions to pass `messages` when calling chat |
| 2 | Re-import `docs/openapi-chatgpt-actions.yaml` (includes `messages` in schema) |
| 3 | Configure LLM provider with API key |
| 4 | Enable **Force model-based intent** in Platform Config → LLM & AI |
| 5 | Ensure Intent prompt is enabled in Model Interactions |
