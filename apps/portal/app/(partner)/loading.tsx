export default function PartnerLoading() {
  return (
    <main className="max-w-[var(--content-max-width)] mx-auto px-6 py-8">
      <div className="animate-pulse flex flex-col gap-4">
        <div className="h-8 bg-[rgb(var(--color-surface))] rounded w-48" />
        <div className="grid gap-4 md:grid-cols-3">
          <div className="h-24 bg-[rgb(var(--color-surface))] rounded-lg" />
          <div className="h-24 bg-[rgb(var(--color-surface))] rounded-lg" />
          <div className="h-24 bg-[rgb(var(--color-surface))] rounded-lg" />
        </div>
      </div>
    </main>
  );
}
