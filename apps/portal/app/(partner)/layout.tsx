import { PartnerNav } from "@/components/partner-nav";

export default function PartnerLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-[rgb(var(--color-background))] text-[rgb(var(--color-text))] flex min-w-0">
      <aside className="w-[var(--sidebar-width)] min-w-[12rem] max-w-[16rem] shrink-0 border-r border-[rgb(var(--color-border))] bg-[rgb(var(--color-surface))] min-h-screen flex flex-col overflow-hidden" aria-label="Partner navigation">
        <PartnerNav />
      </aside>
      <main className="flex-1 min-w-0 overflow-auto">
        {children}
      </main>
    </div>
  );
}
