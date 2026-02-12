# ChatGPT App Directory Submission

How to submit the USO ChatGPT App (MCP server) to the ChatGPT App Directory.

---

## 1. Prerequisites

- [OpenAI Platform](https://platform.openai.com) account
- MCP server deployed and publicly accessible (e.g. Render, Fly.io)
- Apps SDK access (preview as of 2025)

---

## 2. Deploy MCP Server

1. Deploy `apps/uso-chatgpt-app` to a public URL, e.g.:
   - **Render**: New Web Service, build `cd apps/uso-chatgpt-app && npm install && npm run build`, start `npm start`
   - **Fly.io**: `fly launch` in `apps/uso-chatgpt-app`

2. Set environment variables:
   - `ORCHESTRATOR_URL` — your staging/production orchestrator URL
   - `DISCOVERY_URL` — your discovery service URL (if different from orchestrator)

3. Verify the MCP endpoint responds to GET and POST (Streamable HTTP).

---

## 3. Connect from ChatGPT

1. Go to [platform.openai.com](https://platform.openai.com) → Apps or Developer settings.
2. Create a new App or use Apps SDK.
3. Connect your MCP server URL (e.g. `https://uso-mcp.onrender.com`).
4. ChatGPT will discover the 12 tools and allow users to invoke them during conversation.

---

## 4. Submission Checklist

- [ ] MCP server deployed with public HTTPS URL
- [ ] All 12 tools functional (test with MCP client)
- [ ] `ORCHESTRATOR_URL` and `DISCOVERY_URL` set for production
- [ ] Privacy policy URL (required for App Directory)
- [ ] App name and description prepared
- [ ] Follow [OpenAI usage policies](https://openai.com/policies/usage-policies)

---

## 5. References

- [OpenAI Apps SDK](https://developers.openai.com/apps-sdk)
- [Building MCP servers for ChatGPT](https://developers.openai.com/apps-sdk/build/mcp-server)
- [Connect from ChatGPT](https://developers.openai.com/apps-sdk/deploy/connect-chatgpt/)
