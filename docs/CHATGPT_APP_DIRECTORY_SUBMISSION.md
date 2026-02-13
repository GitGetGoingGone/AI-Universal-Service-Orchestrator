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

## 5. Troubleshooting: "Error creating connector" / 500 Internal Server Error

**Symptom:** ChatGPT shows "Received error from MCP server: Server error '500 Internal Server Error'" when creating the connector.

**Causes and fixes:**

1. **Env vars not set on Render** – Ensure `ORCHESTRATOR_URL` and `DISCOVERY_URL` are set in the ChatGPT App service:
   - `ORCHESTRATOR_URL` = `https://uso-orchestrator.onrender.com`
   - `DISCOVERY_URL` = `https://uso-discovery.onrender.com`

2. **Cold start** – On free tier, the service may spin down. Run `./scripts/health-and-warmup.sh` first, or hit `https://uso-chatgpt-app.onrender.com/health` to wake it, then retry the connector.

3. **MCP SDK compatibility** – Ensure `@modelcontextprotocol/sdk` is `^1.0.0` or later. If issues persist, try upgrading: `npm update @modelcontextprotocol/sdk`.

4. **Check Render logs** – Dashboard → uso-chatgpt-app → Logs. Look for "MCP transport error" or stack traces.

5. **URL format** – Use the root URL: `https://uso-chatgpt-app.onrender.com` (no trailing slash). Both `/` and `/mcp` are supported.

6. **"Nothing happens" after entering URL** – ChatGPT may send GET with `Accept: *`; we now add `text/event-stream` so the transport accepts it. Also try `enableJsonResponse: true` for JSON responses. If it still hangs, try the `/mcp` path: `https://uso-chatgpt-app.onrender.com/mcp`.

---

## 7. References

- [OpenAI Apps SDK](https://developers.openai.com/apps-sdk)
- [Building MCP servers for ChatGPT](https://developers.openai.com/apps-sdk/build/mcp-server)
- [Connect from ChatGPT](https://developers.openai.com/apps-sdk/deploy/connect-chatgpt/)
