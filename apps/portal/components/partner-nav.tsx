"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { UserButton } from "@clerk/nextjs";
import {
  LayoutDashboard,
  BarChart3,
  Package,
  ShoppingCart,
  ListTodo,
  DollarSign,
  Megaphone,
  MapPin,
  MessageCircle,
  HeadphonesIcon,
  FileText,
  HelpCircle,
  Users,
  Store,
  Settings,
  Link2,
  Radio,
  BookOpen,
  ClipboardList,
  Zap,
} from "lucide-react";

const NAV_GROUPS = [
  {
    label: "Overview",
    items: [
      { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
      { href: "/actions", label: "Actions", icon: Zap },
      { href: "/analytics", label: "Analytics", icon: BarChart3 },
    ],
  },
  {
    label: "Commerce",
    items: [
      { href: "/products", label: "Products", icon: Package },
      { href: "/orders", label: "Orders", icon: ShoppingCart },
      { href: "/tasks", label: "Tasks", icon: ListTodo },
      { href: "/earnings", label: "Earnings", icon: DollarSign },
      { href: "/promotions", label: "Promotions", icon: Megaphone },
      { href: "/venues", label: "Venues", icon: MapPin },
    ],
  },
  {
    label: "Conversations & support",
    items: [
      { href: "/conversations", label: "Conversations", icon: MessageCircle },
      { href: "/support", label: "Support", icon: HeadphonesIcon },
    ],
  },
  {
    label: "Hub & channels",
    items: [
      { href: "/rfps", label: "Hub RFPs", icon: ClipboardList },
      { href: "/omnichannel", label: "Omnichannel", icon: Radio },
      { href: "/integrations", label: "Integrations", icon: Link2 },
    ],
  },
  {
    label: "Content & team",
    items: [
      { href: "/knowledge-base", label: "Knowledge base", icon: BookOpen },
      { href: "/faqs", label: "FAQs", icon: HelpCircle },
      { href: "/team", label: "Team", icon: Users },
      { href: "/commerce-profile", label: "Commerce profile", icon: Store },
    ],
  },
];

const BOTTOM_ITEMS = [{ href: "/settings", label: "Settings", icon: Settings }];

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

export function PartnerNav() {
  const pathname = usePathname();

  return (
    <div className="flex flex-col h-full min-h-0">
      <div className="p-4 border-b border-[rgb(var(--color-border))] flex items-center justify-between shrink-0">
        <Link
          href="/dashboard"
          className="font-semibold text-lg text-[rgb(var(--color-text))] hover:opacity-90"
          aria-label="USO Partner Portal home"
        >
          USO
        </Link>
        <UserButton afterSignOutUrl="/" />
      </div>
      <nav
        className="flex-1 overflow-y-auto p-3 space-y-4 min-h-0"
        aria-label="Partner portal navigation"
      >
        {NAV_GROUPS.map((group) => (
          <div key={group.label}>
            <p
              className="px-3 mb-1.5 text-xs font-medium uppercase tracking-wider text-[rgb(var(--color-text-secondary))]/80"
              id={`nav-group-${group.label.replace(/\s+/g, "-")}`}
            >
              {group.label}
            </p>
            <ul
              className="space-y-0.5"
              aria-labelledby={`nav-group-${group.label.replace(/\s+/g, "-")}`}
            >
              {group.items.map(({ href, label, icon }) => (
                <li key={href}>
                  <NavLink
                    href={href}
                    label={label}
                    icon={icon}
                    isActive={pathname === href || (href !== "/" && pathname?.startsWith(href))}
                  />
                </li>
              ))}
            </ul>
          </div>
        ))}
        <div className="pt-2 mt-2 border-t border-[rgb(var(--color-border))]">
          <ul className="space-y-0.5">
            {BOTTOM_ITEMS.map(({ href, label, icon }) => (
              <li key={href}>
                <NavLink
                  href={href}
                  label={label}
                  icon={icon}
                  isActive={pathname?.startsWith(href) ?? false}
                />
              </li>
            ))}
          </ul>
        </div>
      </nav>
    </div>
  );
}
