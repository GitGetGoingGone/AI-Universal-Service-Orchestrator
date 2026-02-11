import { NextResponse } from "next/server";
import { getPartnerId } from "@/lib/auth";

const TASK_QUEUE_URL = process.env.TASK_QUEUE_SERVICE_URL || "";

export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const partnerId = await getPartnerId();
  if (!partnerId) {
    return NextResponse.json({ detail: "No partner account" }, { status: 403 });
  }

  if (!TASK_QUEUE_URL) {
    return NextResponse.json({ detail: "TASK_QUEUE_SERVICE_URL not configured" }, { status: 503 });
  }

  const { id } = await params;
  const url = `${TASK_QUEUE_URL.replace(/\/$/, "")}/api/v1/tasks/${id}/start?partner_id=${partnerId}`;

  try {
    const res = await fetch(url, { method: "POST" });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      return NextResponse.json(data || { detail: "Failed to start" }, { status: res.status });
    }
    return NextResponse.json(data);
  } catch (err) {
    return NextResponse.json({ detail: "Task queue unreachable" }, { status: 503 });
  }
}
