"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { UserButton } from "@clerk/nextjs";

const ITEMS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/products", label: "Products" },
  { href: "/schedule", label: "Schedule" },
  { href: "/orders", label: "Orders" },
  { href: "/promotions", label: "Promotions" },
  { href: "/inventory", label: "Inventory" },
  { href: "/venues", label: "Venues" },
  { href: "/settings", label: "Settings" },
];

export function PartnerNav() {
  const pathname = usePathname();
  return (
    <div className="flex flex-col h-full sticky top-0">
      <div className="p-4 border-b border-[rgb(var(--color-border))] flex items-center justify-between">
        <Link href="/dashboard" className="font-semibold text-lg">
          USO
        </Link>
        <UserButton afterSignOutUrl="/" />
      </div>
      <nav className="flex flex-col p-2 gap-0.5 overflow-y-auto">
        {ITEMS.map(({ href, label }) => (
          <Link
            key={href}
            href={href}
            className={`px-3 py-2 rounded-md text-sm ${
              pathname?.startsWith(href)
                ? "bg-[rgb(var(--color-primary))] text-[rgb(var(--color-primary-foreground))] font-medium"
                : "text-[rgb(var(--color-text-secondary))] hover:bg-[rgb(var(--color-border))] hover:text-[rgb(var(--color-text))]"
            }`}
          >
            {label}
          </Link>
        ))}
      </nav>
    </div>
  );
}
