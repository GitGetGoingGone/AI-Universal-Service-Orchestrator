import { NextResponse } from "next/server";
import { getPartnerId } from "@/lib/auth";
import { createSupabaseServerClient } from "@/lib/supabase";

const TASK_QUEUE_URL = process.env.TASK_QUEUE_SERVICE_URL || "";

/**
 * GET /api/partners/actions
 * Returns counts for partner "Actions" overview: pending tasks, unassigned conversations, pending orders.
 */
export async function GET() {
  const partnerId = await getPartnerId();
  if (!partnerId) {
    return NextResponse.json({ detail: "No partner account" }, { status: 403 });
  }

  const supabase = createSupabaseServerClient();

  const [unassignedRes, pendingOrdersRes, pendingTasksCount] = await Promise.all([
    supabase
      .from("conversations")
      .select("id", { count: "exact", head: true })
      .eq("partner_id", partnerId)
      .eq("status", "active")
      .is("assigned_to_member_id", null),
    supabase
      .from("order_legs")
      .select("id", { count: "exact", head: true })
      .eq("partner_id", partnerId)
      .eq("status", "pending"),
    fetchPendingTasksCount(partnerId),
  ]);

  const unassignedConversations = unassignedRes.count ?? 0;
  const pendingOrders = pendingOrdersRes.count ?? 0;

  return NextResponse.json({
    pendingTasks: pendingTasksCount,
    unassignedConversations,
    pendingOrders,
  });
}

async function fetchPendingTasksCount(partnerId: string): Promise<number> {
  if (!TASK_QUEUE_URL) return 0;
  try {
    const url = `${TASK_QUEUE_URL.replace(/\/$/, "")}/api/v1/tasks?partner_id=${partnerId}&status=pending`;
    const res = await fetch(url);
    const data = await res.json().catch(() => []);
    const list = Array.isArray(data) ? data : (data as { tasks?: unknown[] })?.tasks ?? [];
    return list.length;
  } catch {
    return 0;
  }
}
