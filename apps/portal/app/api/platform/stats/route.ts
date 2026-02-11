import { NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/lib/supabase";
import { isPlatformAdmin } from "@/lib/auth";

export async function GET(request: Request) {
  try {
    if (!(await isPlatformAdmin())) {
      return NextResponse.json({ detail: "Platform admin access required" }, { status: 403 });
    }

    const supabase = createSupabaseServerClient();
    const { searchParams } = new URL(request.url);
    const period = searchParams.get("period") || "7d"; // 7d | 30d | all

    const now = new Date();
    const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const startOfWeek = new Date(startOfToday);
    startOfWeek.setDate(startOfWeek.getDate() - 7);
    const startOfMonth = new Date(startOfToday);
    startOfMonth.setDate(startOfMonth.getDate() - 30);

    const periodStart =
      period === "7d" ? startOfWeek.toISOString() : period === "30d" ? startOfMonth.toISOString() : null;

    const ordersQuery = periodStart
      ? supabase.from("orders").select("id,total_amount").gte("created_at", periodStart)
      : supabase.from("orders").select("id,total_amount");

    const results = await Promise.allSettled([
      supabase.from("partners").select("id", { count: "exact", head: true }),
      supabase.from("partners").select("id", { count: "exact", head: true }).eq("verification_status", "pending"),
      supabase.from("bundles").select("id", { count: "exact", head: true }),
      ordersQuery,
      supabase.from("orders").select("id", { count: "exact", head: true }).gte("created_at", startOfToday.toISOString()),
      supabase.from("support_escalations").select("id", { count: "exact", head: true }).eq("status", "pending"),
      supabase.from("vendor_tasks").select("id", { count: "exact", head: true }).eq("status", "pending"),
      supabase.from("rfps").select("id", { count: "exact", head: true }).eq("status", "open"),
    ]);

    const settled = (i: number) => (results[i].status === "fulfilled" ? (results[i] as PromiseFulfilledResult<{ data?: unknown[]; count?: number }>).value : null);
    const partnersRes = settled(0);
    const pendingRes = settled(1);
    const bundlesRes = settled(2);
    const ordersRes = settled(3);
    const ordersTodayRes = settled(4);
    const escalationsRes = settled(5);
    const tasksRes = settled(6);
    const rfpsRes = settled(7);

    const ordersData = ordersRes?.data || [];
    const revenueCents = ordersData.reduce((s, o) => s + Math.round((Number((o as { total_amount?: number })?.total_amount) || 0) * 100), 0);

    return NextResponse.json({
      partners: partnersRes?.count ?? 0,
      pendingApprovals: pendingRes?.count ?? 0,
      activeBundles: bundlesRes?.count ?? 0,
      ordersCount: ordersData.length,
      ordersToday: ordersTodayRes?.count ?? 0,
      revenueCents,
      pendingEscalations: escalationsRes?.count ?? 0,
      vendorTasksPending: tasksRes?.count ?? 0,
      openRfps: rfpsRes?.count ?? 0,
      period,
    });
  } catch (err) {
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
