"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { UserButton } from "@clerk/nextjs";
import {
  LayoutDashboard,
  Users,
  ShoppingCart,
  MessageSquare,
  AlertCircle,
  FileText,
  Settings,
  Shield,
  Package,
  Link2,
} from "lucide-react";

const NAV_GROUPS = [
  {
    label: "Overview",
    items: [{ href: "/platform", label: "Dashboard", icon: LayoutDashboard }],
  },
  {
    label: "Partners & orders",
    items: [
      { href: "/platform/partners", label: "Partners", icon: Users },
      { href: "/platform/partners/ucp", label: "UCP Partners", icon: Link2 },
      { href: "/platform/partners/shopify", label: "Shopify Partners", icon: Package },
      { href: "/platform/orders", label: "Orders", icon: ShoppingCart },
    ],
  },
  {
    label: "Conversations & sessions",
    items: [
      { href: "/platform/experience-sessions", label: "Experience sessions", icon: MessageSquare },
      { href: "/platform/escalations", label: "Escalations", icon: AlertCircle },
    ],
  },
  {
    label: "Hub & config",
    items: [
      { href: "/platform/rfps", label: "RFPs", icon: FileText },
      { href: "/platform/admins", label: "Admins", icon: Shield },
      { href: "/platform/config", label: "Config", icon: Settings },
    ],
  },
];

function NavLink({
  href,
  label,
  icon: Icon,
  isActive,
}: {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  isActive: boolean;
}) {
  return (
    <Link
      href={href}
      className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
        isActive
          ? "bg-[rgb(var(--color-primary))] text-[rgb(var(--color-primary-foreground))] font-medium"
          : "text-[rgb(var(--color-text-secondary))] hover:bg-[rgb(var(--color-border))]/50 hover:text-[rgb(var(--color-text))]"
      }`}
      aria-current={isActive ? "page" : undefined}
    >
      <Icon className="size-4 shrink-0" aria-hidden />
      <span>{label}</span>
    </Link>
  );
}

export function PlatformNav() {
  const pathname = usePathname();

  return (
    <aside
      className="flex flex-col h-full w-56 min-w-0 shrink-0 border-r border-[rgb(var(--color-border))] bg-[rgb(var(--color-surface))] overflow-hidden"
      aria-label="Platform admin navigation"
    >
      <div className="p-4 border-b border-[rgb(var(--color-border))] flex items-center justify-between shrink-0">
        <Link
          href="/platform"
          className="font-semibold text-lg text-[rgb(var(--color-text))] hover:opacity-90"
          aria-label="Platform admin home"
        >
          Platform Admin
        </Link>
        <UserButton afterSignOutUrl="/" />
      </div>
      <nav className="flex-1 overflow-y-auto p-3 space-y-4 min-h-0" aria-label="Platform admin sections">
        {NAV_GROUPS.map((group) => (
          <div key={group.label}>
            <p
              className="px-3 mb-1.5 text-xs font-medium uppercase tracking-wider text-[rgb(var(--color-text-secondary))]/80"
              id={`platform-nav-${group.label.replace(/\s+/g, "-")}`}
            >
              {group.label}
            </p>
            <ul
              className="space-y-0.5"
              aria-labelledby={`platform-nav-${group.label.replace(/\s+/g, "-")}`}
            >
              {group.items.map(({ href, label, icon }) => {
                const isActive =
                  href === "/platform"
                    ? pathname === "/platform"
                    : pathname?.startsWith(href);
                return (
                  <li key={href}>
                    <NavLink href={href} label={label} icon={icon} isActive={!!isActive} />
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>
    </aside>
  );
}
