"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import Link from "next/link";

type RegistryAgent = {
  id: string;
  kind?: string;
  display_name?: string;
  description?: string;
  category?: string;
  enabled?: boolean;
  enabled_default?: boolean;
  user_cancellable?: boolean;
  user_editable?: boolean;
  skills?: Record<string, unknown>;
  plan_template?: string[];
  workflow_order?: number;
};

type MultiAgentConfig = {
  enabled: boolean;
  workflow_order: string[];
  agents: Array<Record<string, unknown>>;
};

function skillsToText(s: unknown): string {
  if (s == null) return "{}";
  try {
    return JSON.stringify(s, null, 2);
  } catch {
    return "{}";
  }
}

function planToText(p: unknown): string {
  if (Array.isArray(p)) return p.map((x) => String(x)).join("\n");
  return "";
}

function parseSkillsJson(raw: string): Record<string, unknown> {
  const t = raw.trim();
  if (!t) return {};
  try {
    const v = JSON.parse(t) as unknown;
    return v && typeof v === "object" && !Array.isArray(v) ? (v as Record<string, unknown>) : { value: v };
  } catch {
    return { raw: t };
  }
}

function parsePlanLines(raw: string): string[] {
  return raw
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean);
}

export function AgentsAdmin() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [globalEnabled, setGlobalEnabled] = useState(true);
  const [workflowText, setWorkflowText] = useState("");
  const [rows, setRows] = useState<RegistryAgent[]>([]);
  const [registryWarning, setRegistryWarning] = useState<string | null>(null);
  /** Remount agent cards after load so defaultValue reflects server data. */
  const [formGeneration, setFormGeneration] = useState(0);

  const workflowOrder = useMemo(
    () => workflowText.split("\n").map((l) => l.trim()).filter(Boolean),
    [workflowText]
  );

  const load = useCallback(async () => {
    setLoading(true);
    setMessage(null);
    try {
      const [cfgRes, regRes] = await Promise.all([
        fetch("/api/platform/config"),
        fetch("/api/platform/multi-agent/registry"),
      ]);
      const cfg = await cfgRes.json();
      const reg = await regRes.json();
      if (cfg.detail && cfgRes.status !== 200) throw new Error(String(cfg.detail));
      const mac = (cfg.multi_agent_config ?? {}) as Partial<MultiAgentConfig>;
      setGlobalEnabled(mac.enabled !== false);
      const wo = Array.isArray(mac.workflow_order) ? mac.workflow_order.map(String) : [];
      setWorkflowText(wo.length ? wo.join("\n") : "");
      if (reg._warning) setRegistryWarning(String(reg._warning));
      else setRegistryWarning(null);
      const agents = Array.isArray(reg.agents) ? (reg.agents as RegistryAgent[]) : [];
      setRows(agents);
      if (!wo.length && agents.length) {
        const sorted = [...agents].sort((a, b) => (a.workflow_order ?? 0) - (b.workflow_order ?? 0));
        setWorkflowText(sorted.map((a) => a.id).join("\n"));
      }
      setFormGeneration((g) => g + 1);
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function onSave() {
    setSaving(true);
    setMessage(null);
    try {
      const agentsPayload = rows.map((a) => {
        const el = document.getElementById(`skills-${a.id}`) as HTMLTextAreaElement | null;
        const pl = document.getElementById(`plan-${a.id}`) as HTMLTextAreaElement | null;
        const dn = document.getElementById(`dn-${a.id}`) as HTMLInputElement | null;
        const ds = document.getElementById(`ds-${a.id}`) as HTMLTextAreaElement | null;
        const en = document.getElementById(`en-${a.id}`) as HTMLInputElement | null;
        const uc = document.getElementById(`uc-${a.id}`) as HTMLInputElement | null;
        const ue = document.getElementById(`ue-${a.id}`) as HTMLInputElement | null;
        const wo = document.getElementById(`wo-${a.id}`) as HTMLInputElement | null;
        return {
          id: a.id,
          display_name: dn?.value?.trim() || a.display_name,
          description: ds?.value ?? a.description,
          enabled: en?.checked ?? a.enabled !== false,
          user_cancellable: uc?.checked ?? !!a.user_cancellable,
          user_editable: ue?.checked ?? !!a.user_editable,
          workflow_order: wo?.value ? Number(wo.value) || a.workflow_order || 0 : a.workflow_order ?? 0,
          skills: el ? parseSkillsJson(el.value) : a.skills ?? {},
          plan_template: pl ? parsePlanLines(pl.value) : a.plan_template ?? [],
        };
      });

      const res = await fetch("/api/platform/config", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          multi_agent_config: {
            enabled: globalEnabled,
            workflow_order: workflowOrder,
            agents: agentsPayload,
          },
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(String(data.detail ?? "Save failed"));
      setMessage("Saved multi-agent configuration.");
      await load();
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <p className="text-sm text-[rgb(var(--color-text-secondary))]">Loading agents…</p>;
  }

  return (
    <div className="space-y-6 max-w-5xl">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-[rgb(var(--color-text-secondary))]">
          Configure discovery scouts, workflow order, plan templates (PAO), skills, and user controls.{" "}
          <Link href="/platform/config" className="underline text-[rgb(var(--color-primary))]">
            Platform config
          </Link>
        </p>
        <Button type="button" onClick={onSave} disabled={saving}>
          {saving ? "Saving…" : "Save multi-agent config"}
        </Button>
      </div>
      {registryWarning && (
        <p className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm text-amber-900 dark:text-amber-100">
          {registryWarning}
        </p>
      )}
      {message && (
        <p
          className={`text-sm ${message.includes("fail") || message.includes("Failed") ? "text-red-600" : "text-emerald-700"}`}
          role="status"
        >
          {message}
        </p>
      )}

      <label className="flex cursor-pointer items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={globalEnabled}
          onChange={(e) => setGlobalEnabled(e.target.checked)}
          className="rounded border-[rgb(var(--color-border))]"
        />
        Multi-agent bundle orchestration enabled
      </label>

      <div>
        <label htmlFor="workflow-order" className="mb-1 block text-sm font-medium text-[rgb(var(--color-text))]">
          Workflow order (one agent id per line)
        </label>
        <textarea
          id="workflow-order"
          value={workflowText}
          onChange={(e) => setWorkflowText(e.target.value)}
          rows={8}
          className="w-full font-mono text-sm rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))] px-3 py-2"
          spellCheck={false}
        />
      </div>

      <div className="space-y-4">
        <h2 className="text-lg font-semibold text-[rgb(var(--color-text))]">Agents</h2>
        <ul className="space-y-4" key={formGeneration}>
          {rows.map((a) => (
            <li
              key={a.id}
              className="rounded-xl border border-[rgb(var(--color-border))] bg-[rgb(var(--color-surface))] p-4 space-y-3"
            >
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-mono text-xs text-[rgb(var(--color-text-secondary))]">{a.id}</span>
                {a.category ? (
                  <span className="rounded-full bg-[rgb(var(--color-border))]/40 px-2 py-0.5 text-xs">{a.category}</span>
                ) : null}
                {a.kind ? <span className="text-xs text-[rgb(var(--color-text-secondary))]">{a.kind}</span> : null}
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                <div>
                  <label htmlFor={`dn-${a.id}`} className="text-xs font-medium text-[rgb(var(--color-text-secondary))]">
                    Display name
                  </label>
                  <input
                    id={`dn-${a.id}`}
                    type="text"
                    defaultValue={a.display_name ?? a.id}
                    className="mt-1 w-full rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))] px-2 py-1.5 text-sm"
                  />
                </div>
                <div>
                  <label htmlFor={`wo-${a.id}`} className="text-xs font-medium text-[rgb(var(--color-text-secondary))]">
                    Workflow order (sort key)
                  </label>
                  <input
                    id={`wo-${a.id}`}
                    type="number"
                    defaultValue={a.workflow_order ?? 0}
                    className="mt-1 w-full rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))] px-2 py-1.5 text-sm"
                  />
                </div>
              </div>
              <div>
                <label htmlFor={`ds-${a.id}`} className="text-xs font-medium text-[rgb(var(--color-text-secondary))]">
                  Description
                </label>
                <textarea
                  id={`ds-${a.id}`}
                  defaultValue={a.description ?? ""}
                  rows={2}
                  className="mt-1 w-full rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))] px-2 py-1.5 text-sm"
                />
              </div>
              <div className="flex flex-wrap gap-4 text-sm">
                <label className="flex items-center gap-2">
                  <input id={`en-${a.id}`} type="checkbox" defaultChecked={a.enabled !== false} className="rounded" />
                  Enabled
                </label>
                <label className="flex items-center gap-2">
                  <input id={`uc-${a.id}`} type="checkbox" defaultChecked={!!a.user_cancellable} className="rounded" />
                  User can skip / cancel
                </label>
                <label className="flex items-center gap-2">
                  <input id={`ue-${a.id}`} type="checkbox" defaultChecked={!!a.user_editable} className="rounded" />
                  User-editable skills in chat
                </label>
              </div>
              <div>
                <label htmlFor={`skills-${a.id}`} className="text-xs font-medium text-[rgb(var(--color-text-secondary))]">
                  Skills (JSON)
                </label>
                <textarea
                  id={`skills-${a.id}`}
                  defaultValue={skillsToText(a.skills)}
                  rows={4}
                  spellCheck={false}
                  className="mt-1 w-full font-mono text-xs rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))] px-2 py-1.5"
                />
              </div>
              <div>
                <label htmlFor={`plan-${a.id}`} className="text-xs font-medium text-[rgb(var(--color-text-secondary))]">
                  Plan template (PAO — one step label per line)
                </label>
                <textarea
                  id={`plan-${a.id}`}
                  defaultValue={planToText(a.plan_template)}
                  rows={4}
                  className="mt-1 w-full rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))] px-2 py-1.5 text-sm"
                  spellCheck={false}
                />
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
