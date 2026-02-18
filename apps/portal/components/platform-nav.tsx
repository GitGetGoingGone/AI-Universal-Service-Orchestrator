"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { UserButton } from "@clerk/nextjs";

const NAV_ITEMS = [
  { href: "/platform", label: "Dashboard", description: "Platform metrics and overview" },
  { href: "/platform/partners", label: "Partners", description: "Manage partner accounts and onboarding" },
  { href: "/platform/escalations", label: "Escalations", description: "Support escalations and assignments" },
  { href: "/platform/rfps", label: "RFPs", description: "Hub RFPs and bid management" },
  { href: "/platform/admins", label: "Admins", description: "Platform admin users" },
  { href: "/platform/config", label: "Algorithms & Config", description: "LLM, ranking, discovery, and integrations" },
];

export function PlatformNav() {
  const pathname = usePathname();
  const isLoginOrAccessDenied =
    pathname === "/platform/login" || pathname === "/platform/access-denied";

  if (isLoginOrAccessDenied) return null;

  return (
    <div className="flex flex-col h-full w-56 shrink-0 border-r border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]">
      <div className="p-4 border-b border-[rgb(var(--color-border))] flex items-center justify-between">
        <Link href="/platform" className="font-semibold text-lg">
          Platform Admin
        </Link>
        <UserButton afterSignOutUrl="/" />
      </div>
      <nav className="flex flex-col p-2 gap-0.5 overflow-y-auto flex-1">
        {NAV_ITEMS.map(({ href, label, description }) => {
          const isActive =
            href === "/platform"
              ? pathname === "/platform"
              : pathname?.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={`block px-3 py-2.5 rounded-md text-sm group ${
                isActive
                  ? "bg-[rgb(var(--color-primary))] text-[rgb(var(--color-primary-foreground))] font-medium"
                  : "text-[rgb(var(--color-text-secondary))] hover:bg-[rgb(var(--color-border))] hover:text-[rgb(var(--color-text))]"
              }`}
              title={description}
            >
              <span className="block font-medium">{label}</span>
              <span
                className={`block text-xs mt-0.5 ${
                  isActive
                    ? "opacity-90"
                    : "text-[rgb(var(--color-text-secondary))] opacity-80"
                }`}
              >
                {description}
              </span>
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
