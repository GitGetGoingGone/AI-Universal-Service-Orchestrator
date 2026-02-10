import { auth, currentUser } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/lib/supabase";

export async function POST(request: Request) {
  try {
    const { userId } = await auth();
    if (!userId) {
      return NextResponse.json(
        { detail: "Sign in required. Create an account first, then register your business." },
        { status: 401 }
      );
    }

    const user = await currentUser();
    const emails = user?.emailAddresses?.map((e) => e.emailAddress).filter(Boolean) ?? [];
    const contactEmail = emails[0];
    if (!contactEmail) {
      return NextResponse.json(
        { detail: "Your account must have a verified email to register as a partner." },
        { status: 400 }
      );
    }

    const body = await request.json();
    const { business_name, business_type } = body;

    if (!business_name) {
      return NextResponse.json(
        { detail: "business_name is required" },
        { status: 400 }
      );
    }

    const supabase = createSupabaseServerClient();

    // Check for existing partner with this email (avoid duplicates)
    const { data: existing } = await supabase
      .from("partners")
      .select("id, verification_status")
      .eq("contact_email", contactEmail)
      .eq("is_active", true)
      .limit(1)
      .single();

    if (existing) {
      return NextResponse.json(
        {
          detail:
            existing.verification_status === "pending"
              ? "You already have a pending application."
              : "A partner account already exists for this email.",
        },
        { status: 409 }
      );
    }

    const { data, error } = await supabase
      .from("partners")
      .insert({
        business_name,
        contact_email: contactEmail,
        business_type: business_type || null,
        verification_status: "pending",
        is_active: true,
      })
      .select("id")
      .single();

    if (error) {
      console.error("Partner registration error:", error);
      return NextResponse.json(
        { detail: error.message },
        { status: 500 }
      );
    }

    return NextResponse.json({ id: data.id, status: "pending" });
  } catch (err) {
    console.error("Partner registration error:", err);
    return NextResponse.json(
      { detail: "Internal server error" },
      { status: 500 }
    );
  }
}
