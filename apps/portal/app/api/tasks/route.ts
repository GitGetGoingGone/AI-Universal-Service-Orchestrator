import { NextResponse } from "next/server";
import { getPartnerId } from "@/lib/auth";

const TASK_QUEUE_URL = process.env.TASK_QUEUE_SERVICE_URL || "";

export async function GET(request: Request) {
  const partnerId = await getPartnerId();
  if (!partnerId) {
    return NextResponse.json({ detail: "No partner account" }, { status: 403 });
  }

  if (!TASK_QUEUE_URL) {
    return NextResponse.json({ detail: "TASK_QUEUE_SERVICE_URL not configured" }, { status: 503 });
  }

  const { searchParams } = new URL(request.url);
  const status = searchParams.get("status") || "pending";
  const url = `${TASK_QUEUE_URL.replace(/\/$/, "")}/api/v1/tasks?partner_id=${partnerId}&status=${status}`;

  try {
    const res = await fetch(url);
    const data = await res.json().catch(() => []);
    if (!res.ok) {
      return NextResponse.json(data || { detail: "Task queue error" }, { status: res.status });
    }
    return NextResponse.json(Array.isArray(data) ? data : data.tasks ?? []);
  } catch (err) {
    return NextResponse.json({ detail: "Task queue unreachable" }, { status: 503 });
  }
}
