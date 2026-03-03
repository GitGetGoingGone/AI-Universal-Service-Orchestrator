"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

type UCPPartner = {
  id: string;
  base_url: string;
  display_name: string | null;
  enabled: boolean;
  available_to_customize?: boolean;
  price_premium_percent?: number;
  has_token?: boolean;
  created_at: string;
  updated_at: string;
};

export function UCPPartnersList() {
  const [list, setList] = useState<UCPPartner[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<{
    display_name: string;
    enabled: boolean;
    price_premium_percent: number;
    available_to_customize: boolean;
    access_token: string;
  }>({
    display_name: "",
    enabled: true,
    price_premium_percent: 0,
    available_to_customize: false,
    access_token: "",
  });

  async function fetchList() {
    setLoading(true);
    try {
      const res = await fetch("/api/platform/ucp-partners");
      if (!res.ok) throw new Error("Failed to load");
      const data = await res.json();
      setList(data.ucp_partners ?? []);
    } catch {
      setList([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchList();
  }, []);

  function startEdit(row: UCPPartner) {
    setEditingId(row.id);
    setEditForm({
      display_name: row.display_name ?? row.base_url,
      enabled: row.enabled,
      price_premium_percent: Number(row.price_premium_percent) ?? 0,
      available_to_customize: Boolean(row.available_to_customize),
      access_token: "",
    });
  }

  async function saveEdit() {
    if (!editingId) return;
    const payload: Record<string, unknown> = {
      display_name: editForm.display_name,
      enabled: editForm.enabled,
      price_premium_percent: editForm.price_premium_percent,
      available_to_customize: editForm.available_to_customize,
    };
    if (editForm.access_token.trim()) payload.access_token = editForm.access_token.trim();
    try {
      const res = await fetch(`/api/platform/ucp-partners/${editingId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error((d as { detail?: string }).detail || "Failed");
      }
      setEditingId(null);
      setEditForm({
        display_name: "",
        enabled: true,
        price_premium_percent: 0,
        available_to_customize: false,
        access_token: "",
      });
      fetchList();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Failed to save");
    }
  }

  function cancelEdit() {
    setEditingId(null);
  }

  if (loading) return <p className="text-[rgb(var(--color-text-secondary))]">Loading...</p>;

  if (list.length === 0) {
    return (
      <div className="rounded-lg border border-[rgb(var(--color-border))] bg-[rgb(var(--color-surface))] p-8 text-center">
        <p className="text-[rgb(var(--color-text-secondary))] mb-4">No UCP partners yet.</p>
        <Button asChild size="sm">
          <Link href="/platform/partners/ucp-new">Add UCP partner</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="border border-[rgb(var(--color-border))] rounded-lg overflow-x-auto">
      <table className="w-full min-w-[800px]">
        <thead className="bg-[rgb(var(--color-surface))]">
          <tr>
            <th className="text-left px-4 py-2">Display name</th>
            <th className="text-left px-4 py-2">Base URL</th>
            <th className="text-left px-4 py-2">Premium %</th>
            <th className="text-left px-4 py-2">Customize</th>
            <th className="text-left px-4 py-2">Token</th>
            <th className="text-left px-4 py-2">Enabled</th>
            <th className="text-left px-4 py-2">Updated</th>
            <th className="w-28 px-4 py-2">Actions</th>
          </tr>
        </thead>
        <tbody>
          {list.map((row) => (
            <tr key={row.id} className="border-t border-[rgb(var(--color-border))]">
              {editingId === row.id ? (
                <>
                  <td className="px-4 py-2">
                    <input
                      type="text"
                      value={editForm.display_name}
                      onChange={(e) => setEditForm((f) => ({ ...f, display_name: e.target.value }))}
                      placeholder="Display name"
                      className="w-full max-w-xs px-2 py-1.5 rounded border border-[rgb(var(--color-border))] text-sm"
                    />
                  </td>
                  <td className="px-4 py-2 font-mono text-xs max-w-[200px] truncate" title={row.base_url}>
                    {row.base_url}
                  </td>
                  <td className="px-4 py-2">
                    <input
                      type="number"
                      min={0}
                      step={0.01}
                      value={editForm.price_premium_percent}
                      onChange={(e) =>
                        setEditForm((f) => ({ ...f, price_premium_percent: Number(e.target.value) }))
                      }
                      className="w-20 px-2 py-1.5 rounded border border-[rgb(var(--color-border))] text-sm"
                    />
                  </td>
                  <td className="px-4 py-2">
                    <label className="flex items-center gap-1">
                      <input
                        type="checkbox"
                        checked={editForm.available_to_customize}
                        onChange={(e) =>
                          setEditForm((f) => ({ ...f, available_to_customize: e.target.checked }))
                        }
                        className="rounded"
                      />
                      <span className="text-sm">Yes</span>
                    </label>
                  </td>
                  <td className="px-4 py-2">
                    <input
                      type="password"
                      value={editForm.access_token}
                      onChange={(e) => setEditForm((f) => ({ ...f, access_token: e.target.value }))}
                      placeholder={row.has_token ? "Leave blank to keep" : "Optional"}
                      className="w-28 px-2 py-1.5 rounded border border-[rgb(var(--color-border))] text-sm"
                    />
                  </td>
                  <td className="px-4 py-2">
                    <label className="flex items-center gap-1">
                      <input
                        type="checkbox"
                        checked={editForm.enabled}
                        onChange={(e) => setEditForm((f) => ({ ...f, enabled: e.target.checked }))}
                        className="rounded"
                      />
                      <span className="text-sm">Enabled</span>
                    </label>
                  </td>
                  <td className="px-4 py-2 text-sm text-[rgb(var(--color-text-secondary))]">
                    {row.updated_at ? new Date(row.updated_at).toLocaleString() : "—"}
                  </td>
                  <td className="px-4 py-2">
                    <div className="flex gap-1">
                      <Button size="sm" onClick={saveEdit}>Save</Button>
                      <Button size="sm" variant="outline" onClick={cancelEdit}>Cancel</Button>
                    </div>
                  </td>
                </>
              ) : (
                <>
                  <td className="px-4 py-2 font-medium">{row.display_name || row.base_url}</td>
                  <td className="px-4 py-2 font-mono text-xs max-w-[280px] truncate" title={row.base_url}>
                    {row.base_url}
                  </td>
                  <td className="px-4 py-2">{Number(row.price_premium_percent ?? 0)}%</td>
                  <td className="px-4 py-2">
                    {row.available_to_customize ? (
                      <span className="text-green-600 dark:text-green-400">Yes</span>
                    ) : (
                      <span className="text-[rgb(var(--color-text-secondary))]">No</span>
                    )}
                  </td>
                  <td className="px-4 py-2">
                    {row.has_token ? (
                      <span className="text-xs text-green-600 dark:text-green-400">Set</span>
                    ) : (
                      <span className="text-xs text-[rgb(var(--color-text-secondary))]">—</span>
                    )}
                  </td>
                  <td className="px-4 py-2">
                    {row.enabled ? (
                      <span className="text-green-600 dark:text-green-400">Yes</span>
                    ) : (
                      <span className="text-[rgb(var(--color-text-secondary))]">No</span>
                    )}
                  </td>
                  <td className="px-4 py-2 text-sm text-[rgb(var(--color-text-secondary))]">
                    {row.updated_at ? new Date(row.updated_at).toLocaleString() : "—"}
                  </td>
                  <td className="px-4 py-2">
                    <Button size="sm" variant="outline" onClick={() => startEdit(row)}>
                      Edit
                    </Button>
                  </td>
                </>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
