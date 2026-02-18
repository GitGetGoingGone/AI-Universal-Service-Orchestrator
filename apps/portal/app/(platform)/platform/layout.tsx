import { PlatformNav } from "@/components/platform-nav";

export default function PlatformSectionLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen flex bg-[rgb(var(--color-background))] text-[rgb(var(--color-text))]">
      <PlatformNav />
      <div className="flex-1 min-w-0">{children}</div>
    </div>
  );
}
