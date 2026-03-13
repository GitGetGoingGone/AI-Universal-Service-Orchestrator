"use client";

import { usePathname } from "next/navigation";
import { PlatformNav } from "@/components/platform-nav";

const NO_NAV_PATHS = ["/platform/login", "/platform/access-denied"];

export function PlatformLayoutClient({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  /* Hide nav on login/access-denied; also when pathname is not yet available (e.g. initial paint) to avoid flashing nav */
  const hideNav = !pathname || NO_NAV_PATHS.includes(pathname);

  if (hideNav) {
    return (
      <div className="min-h-screen flex flex-col bg-[rgb(var(--color-background))] text-[rgb(var(--color-text))]">
        <div className="flex-1 min-w-0">{children}</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex bg-[rgb(var(--color-background))] text-[rgb(var(--color-text))] min-w-0">
      <PlatformNav />
      <div className="flex-1 min-w-0 overflow-auto">{children}</div>
    </div>
  );
}
