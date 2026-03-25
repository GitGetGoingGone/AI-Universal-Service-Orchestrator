import { AgentsAdmin } from "./agents-admin";

export const metadata = {
  title: "Multi-agent scouts | Platform",
};

export default function PlatformAgentsPage() {
  return (
    <div className="p-6 md:p-8 max-w-6xl mx-auto">
      <header className="mb-8">
        <h1 className="text-2xl font-semibold text-[rgb(var(--color-text))]">Multi-agent scouts</h1>
        <p className="mt-1 text-sm text-[rgb(var(--color-text-secondary))]">
          Registry, workflow, skills, plan templates, and user-facing controls for bundle discovery agents.
        </p>
      </header>
      <AgentsAdmin />
    </div>
  );
}
