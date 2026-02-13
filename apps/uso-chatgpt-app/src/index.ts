#!/usr/bin/env node
/**
 * MCP server for ChatGPT App Directory.
 * 12 tools for AI Universal Service Orchestrator: discover, products, bundles, checkout, manifest, orders, support, returns.
 *
 * Uses per-request transport (stateless pattern) for compatibility with ChatGPT connector creation.
 */

import { createServer, type IncomingMessage, type ServerResponse } from "node:http";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { z } from "zod";
import * as client from "./client.js";

const PORT = parseInt(process.env.PORT || "3010", 10);

/** Creates a fresh MCP server with all tools (per-request for stateless operation). */
function createMcpServer(): McpServer {
  const mcp = new McpServer(
    { name: "uso-chatgpt-app", version: "0.1.0" },
    { instructions: "AI Universal Service Orchestrator: discover products, bundles, checkout, order tracking, support, returns." }
  );

  mcp.registerTool("discover_products", {
    description: "Search products by intent/query",
    inputSchema: z.object({
      query: z.string().describe("Search query, e.g. 'flowers', 'chocolates'"),
      limit: z.number().optional().default(20),
      partner_id: z.string().optional(),
    }),
  }, async (args) => {
    const data = await client.discoverProducts(args.query, args.limit, args.partner_id);
    return { content: [{ type: "text", text: JSON.stringify(data) }] };
  });

  mcp.registerTool("get_product_details", {
    description: "Get product by ID",
    inputSchema: z.object({ product_id: z.string() }),
  }, async (args) => {
    const data = await client.getProductDetails(args.product_id);
    return { content: [{ type: "text", text: JSON.stringify(data) }] };
  });

  mcp.registerTool("get_bundle_details", {
    description: "Get bundle by ID",
    inputSchema: z.object({ bundle_id: z.string() }),
  }, async (args) => {
    const data = await client.getBundleDetails(args.bundle_id);
    return { content: [{ type: "text", text: JSON.stringify(data) }] };
  });

  mcp.registerTool("add_to_bundle", {
    description: "Add product to bundle",
    inputSchema: z.object({
      product_id: z.string(),
      user_id: z.string().optional(),
      bundle_id: z.string().optional(),
    }),
  }, async (args) => {
    const data = await client.addToBundle(args.product_id, args.user_id, args.bundle_id);
    return { content: [{ type: "text", text: JSON.stringify(data) }] };
  });

  mcp.registerTool("remove_from_bundle", {
    description: "Remove item from bundle (item_id is bundle_leg id)",
    inputSchema: z.object({ item_id: z.string() }),
  }, async (args) => {
    const data = await client.removeFromBundle(args.item_id);
    return { content: [{ type: "text", text: JSON.stringify(data) }] };
  });

  mcp.registerTool("proceed_to_checkout", {
    description: "Start checkout with bundle",
    inputSchema: z.object({ bundle_id: z.string() }),
  }, async (args) => {
    const data = await client.proceedToCheckout(args.bundle_id);
    return { content: [{ type: "text", text: JSON.stringify(data) }] };
  });

  mcp.registerTool("create_payment_intent", {
    description: "Create Stripe payment intent for order",
    inputSchema: z.object({ order_id: z.string() }),
  }, async (args) => {
    const data = await client.createPaymentIntent(args.order_id);
    return { content: [{ type: "text", text: JSON.stringify(data) }] };
  });

  mcp.registerTool("request_change", {
    description: "Request order change (e.g. different item); notifies partner",
    inputSchema: z.object({
      order_id: z.string(),
      order_leg_id: z.string(),
      partner_id: z.string(),
      original_item: z.record(z.unknown()),
      requested_change: z.record(z.unknown()),
      respond_by: z.string().optional(),
    }),
  }, async (args) => {
    const data = await client.requestChange(
      args.order_id,
      args.order_leg_id,
      args.partner_id,
      args.original_item as Record<string, unknown>,
      args.requested_change as Record<string, unknown>,
      args.respond_by
    );
    return { content: [{ type: "text", text: JSON.stringify(data) }] };
  });

  mcp.registerTool("get_manifest", {
    description: "Get platform capabilities and action models for AI agents",
    inputSchema: z.object({}),
  }, async () => {
    const data = await client.getManifest();
    return { content: [{ type: "text", text: JSON.stringify(data) }] };
  });

  mcp.registerTool("track_order", {
    description: "Get order status",
    inputSchema: z.object({ order_id: z.string() }),
  }, async (args) => {
    const data = await client.trackOrder(args.order_id);
    return { content: [{ type: "text", text: JSON.stringify(data) }] };
  });

  mcp.registerTool("classify_support", {
    description: "Route support message (AI vs human)",
    inputSchema: z.object({
      conversation_ref: z.string(),
      message_content: z.string(),
    }),
  }, async (args) => {
    const data = await client.classifySupport(args.conversation_ref, args.message_content);
    return { content: [{ type: "text", text: JSON.stringify(data) }] };
  });

  mcp.registerTool("create_return", {
    description: "Create return request for order",
    inputSchema: z.object({
      order_id: z.string(),
      partner_id: z.string(),
      reason: z.string().optional(),
      reason_detail: z.string().optional(),
      order_leg_id: z.string().optional(),
      requester_id: z.string().optional(),
      refund_amount_cents: z.number().optional(),
    }),
  }, async (args) => {
    const data = await client.createReturn(args.order_id, args.partner_id, {
      reason: args.reason,
      reason_detail: args.reason_detail,
      order_leg_id: args.order_leg_id,
      requester_id: args.requester_id,
      refund_amount_cents: args.refund_amount_cents,
    });
    return { content: [{ type: "text", text: JSON.stringify(data) }] };
  });

  return mcp;
}

function safeWriteError(res: ServerResponse, status: number, message: string) {
  if (!res.headersSent) {
    res.writeHead(status, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ error: "Internal Server Error", message }));
  }
}

function logRequest(req: IncomingMessage) {
  const url = req.url ?? "/";
  const accept = (req.headers["accept"] ?? "").slice(0, 100);
  console.log(`[MCP] ${req.method} ${url} | Accept: ${accept || "(none)"}`);
}

const server = createServer((req, res) => {
  // Health check for Render / load balancers
  if (req.url === "/health" && req.method === "GET") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ status: "ok", service: "uso-chatgpt-app" }));
    return;
  }

  if (req.method === "GET" || req.method === "POST") {
    logRequest(req);
    (async () => {
      const mcpServer = createMcpServer();
      const transport = new StreamableHTTPServerTransport({
        sessionIdGenerator: undefined,
      });
      transport.onerror = (err) => console.error("[MCP] transport error:", err);

      try {
        await mcpServer.connect(transport);
        await transport.handleRequest(req as Parameters<typeof transport.handleRequest>[0], res);
      } catch (err) {
        console.error("[MCP] handleRequest error:", err);
        safeWriteError(res, 500, String(err));
      } finally {
        res.on("close", () => {
          transport.close().catch(() => {});
          mcpServer.close().catch(() => {});
        });
      }
    })();
  } else {
    res.writeHead(405);
    res.end("Method Not Allowed");
  }
});

server.on("clientError", (err, socket) => {
  console.error("Client error:", err);
  socket.destroy();
});

server.listen(PORT, () => {
  console.log(`USO ChatGPT MCP server listening on http://localhost:${PORT}`);
  console.log("ORCHESTRATOR_URL:", process.env.ORCHESTRATOR_URL || "http://localhost:8002");
  console.log("DISCOVERY_URL:", process.env.DISCOVERY_URL || "http://localhost:8000");
});
