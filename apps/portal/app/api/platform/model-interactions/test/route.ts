import { NextResponse } from "next/server";
import { isPlatformAdmin } from "@/lib/auth";

const ORCHESTRATOR_URL =
  process.env.ORCHESTRATOR_SERVICE_URL || "https://uso-orchestrator.onrender.com";

export async function POST(request: Request) {
  try {
    if (!(await isPlatformAdmin())) {
      return NextResponse.json(
        { detail: "Platform admin access required" },
        { status: 403 }
      );
    }

    const body = await request.json();
    const { interaction_type, sample_user_message, system_prompt_override } =
      body;

    if (!interaction_type) {
      return NextResponse.json(
        { detail: "interaction_type required" },
        { status: 400 }
      );
    }

    const res = await fetch(
      `${ORCHESTRATOR_URL.replace(/\/$/, "")}/api/v1/admin/test-interaction`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          interaction_type,
          sample_user_message: sample_user_message || undefined,
          system_prompt_override: system_prompt_override || undefined,
        }),
      }
    );

    const data = await res.json().catch(() => ({}));

    if (!res.ok) {
      return NextResponse.json(
        { detail: data.detail || "Orchestrator test failed" },
        { status: res.status }
      );
    }

    return NextResponse.json(data);
  } catch (err) {
    return NextResponse.json(
      { detail: "Internal server error" },
      { status: 500 }
    );
  }
}
