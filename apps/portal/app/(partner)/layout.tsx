import { PartnerNav } from "@/components/partner-nav";

export default function PartnerLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-[rgb(var(--color-background))] text-[rgb(var(--color-text))] flex">
      <aside className="w-[var(--sidebar-width)] min-w-[12rem] shrink-0 border-r border-[rgb(var(--color-border))] bg-[rgb(var(--color-surface))] min-h-screen">
        <PartnerNav />
      </aside>
      <main className="flex-1 min-w-0">
        {children}
      </main>
    </div>
  );
}
