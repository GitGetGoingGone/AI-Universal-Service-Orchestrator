import { NextResponse } from "next/server";
import { auth } from "@clerk/nextjs/server";
import { getPartnerStatus } from "@/lib/auth";

export async function GET() {
  const { userId } = await auth();
  if (!userId) {
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  }

  const status = await getPartnerStatus();
  if (!status) {
    return NextResponse.json({
      partner: null,
      message: "No partner account found. Use the same email as your registration, or contact support.",
    });
  }

  return NextResponse.json({
    partner: { id: status.partnerId, verification_status: status.status },
    message: status.status === "pending"
      ? "Your application is pending approval."
      : undefined,
  });
}
