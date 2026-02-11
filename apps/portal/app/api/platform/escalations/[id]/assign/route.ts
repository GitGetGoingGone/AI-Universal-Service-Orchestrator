import { NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/lib/supabase";
import { isPlatformAdmin } from "@/lib/auth";

export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    if (!(await isPlatformAdmin())) {
      return NextResponse.json({ detail: "Platform admin access required" }, { status: 403 });
    }

    const { id } = await params;
    const body = await request.json();
    const assignedTo = body?.assigned_to as string | undefined;
    const assignedToClerkId = body?.assigned_to_clerk_id as string | undefined;

    if (!assignedTo && !assignedToClerkId) {
      return NextResponse.json({ detail: "assigned_to or assigned_to_clerk_id required" }, { status: 400 });
    }

    const supabase = createSupabaseServerClient();
    const update: Record<string, unknown> = { status: "assigned" };
    if (assignedTo) update.assigned_to = assignedTo;
    if (assignedToClerkId) update.assigned_to_clerk_id = assignedToClerkId;
    if (!assignedTo) update.assigned_to = null;

    const { data, error } = await supabase
      .from("support_escalations")
      .update(update)
      .eq("id", id)
      .select()
      .single();

    if (error) {
      return NextResponse.json({ detail: error.message }, { status: error.code === "PGRST116" ? 404 : 500 });
    }

    return NextResponse.json(data);
  } catch (err) {
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
