import { ConversationsDashboard } from "./conversations-dashboard";

export const metadata = {
  title: "Conversations & cost | Platform",
};

export default function PlatformConversationsPage() {
  return (
    <div className="p-6 md:p-8 max-w-6xl mx-auto">
      <header className="mb-8">
        <h1 className="text-2xl font-semibold text-[rgb(var(--color-text))]">Conversations & cost</h1>
        <p className="mt-1 text-sm text-[rgb(var(--color-text-secondary))]">
          Per-thread metrics: thought timelines, memory health, and estimated token usage aggregated from chat runs.
        </p>
      </header>
      <ConversationsDashboard />
    </div>
  );
}
