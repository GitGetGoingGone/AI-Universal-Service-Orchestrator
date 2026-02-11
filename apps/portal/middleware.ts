import { clerkMiddleware } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";
import { isPlatformAdminByUserId } from "@/lib/auth";

export default clerkMiddleware(async (auth, req) => {
  const pathname = req.nextUrl?.pathname ?? new URL(req.url).pathname ?? "";
  if (!pathname) return;

  // Public routes: landing, register, sign-in, sign-up, API
  if (
    pathname === "/" ||
    pathname.startsWith("/register") ||
    pathname.startsWith("/sign-in") ||
    pathname.startsWith("/sign-up") ||
    pathname.startsWith("/api/") ||
    pathname === "/platform/login" ||
    pathname === "/platform/access-denied"
  ) {
    return;
  }

  if (pathname.startsWith("/platform")) {
    const { userId } = await auth();
    if (!userId) {
      return NextResponse.redirect(new URL("/platform/login", req.url));
    }
    // Restrict platform portal to authorized admins only
    const isAdmin = await isPlatformAdminByUserId(userId);
    if (!isAdmin) {
      return NextResponse.redirect(new URL("/platform/access-denied", req.url));
    }
    return;
  }

  if (
    pathname.startsWith("/dashboard") ||
    pathname.startsWith("/products") ||
    pathname.startsWith("/schedule") ||
    pathname.startsWith("/orders") ||
    pathname.startsWith("/earnings") ||
    pathname.startsWith("/analytics") ||
    pathname.startsWith("/promotions") ||
    pathname.startsWith("/inventory") ||
    pathname.startsWith("/ratings") ||
    pathname.startsWith("/venues") ||
    pathname.startsWith("/team") ||
    pathname.startsWith("/admins") ||
    pathname.startsWith("/settings") ||
    pathname.startsWith("/integrations") ||
    pathname.startsWith("/omnichannel") ||
    pathname.startsWith("/conversations") ||
    pathname.startsWith("/knowledge-base") ||
    pathname.startsWith("/faqs") ||
    pathname.startsWith("/tasks") ||
    pathname.startsWith("/rfps") ||
    pathname.startsWith("/support") ||
    pathname.startsWith("/commerce-profile") ||
    pathname.startsWith("/pay")
  ) {
    await auth.protect();
    return;
  }
});

export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|ico|svg|woff2?|ttf|otf)$).*)",
  ],
};
