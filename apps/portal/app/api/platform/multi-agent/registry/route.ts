import { NextResponse } from "next/server";
import { isPlatformAdmin } from "@/lib/auth";

const ORCHESTRATOR_URL = (
  process.env.ORCHESTRATOR_SERVICE_URL || "https://uso-orchestrator.onrender.com"
).replace(/\/$/, "");

/** Fallback when orchestrator is unreachable (ids must match orchestrator agent_registry). */
const REGISTRY_FALLBACK = {
  enabled: true,
  workflow_order: [
    "local_db_bundle_agent",
    "ucp_bundle_agent",
    "mcp_bundle_agent",
    "weather_context_agent",
    "events_context_agent",
    "resourcing_agent",
  ],
  agents: [] as unknown[],
};

export async function GET() {
  try {
    if (!(await isPlatformAdmin())) {
      return NextResponse.json({ detail: "Platform admin access required" }, { status: 403 });
    }

    const res = await fetch(`${ORCHESTRATOR_URL}/api/v1/multi-agent/registry`, {
      headers: { Accept: "application/json" },
      cache: "no-store",
    });

    if (!res.ok) {
      const text = await res.text().catch(() => "");
      return NextResponse.json(
        {
          ...REGISTRY_FALLBACK,
          _warning: `Orchestrator registry unavailable (${res.status}). Using fallback ids. ${text.slice(0, 200)}`,
        },
        { status: 200 }
      );
    }

    const data = (await res.json()) as Record<string, unknown>;
    return NextResponse.json(data);
  } catch (err) {
    return NextResponse.json(
      {
        ...REGISTRY_FALLBACK,
        _warning: err instanceof Error ? err.message : "Registry fetch failed",
      },
      { status: 200 }
    );
  }
}
