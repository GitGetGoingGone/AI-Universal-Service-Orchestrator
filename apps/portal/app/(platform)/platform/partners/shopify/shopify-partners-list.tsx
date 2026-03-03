"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

type ShopifyPartner = {
  id: string;
  partner_id: string;
  internal_agent_registry_id: string;
  shop_url: string;
  mcp_endpoint: string;
  supported_capabilities: string[];
  price_premium_percent: number;
  access_token_vault_ref: string | null;
  created_at: string;
  updated_at: string;
  business_name: string | null;
  display_name: string | null;
  available_to_customize: boolean;
  enabled: boolean;
};

export function ShopifyPartnersList() {
  const [list, setList] = useState<ShopifyPartner[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<Partial<ShopifyPartner>>({});

  async function fetchList() {
    setLoading(true);
    try {
      const res = await fetch("/api/platform/shopify-partners");
      if (!res.ok) throw new Error("Failed to load");
      const data = await res.json();
      setList(data.shopify_partners ?? []);
    } catch {
      setList([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchList();
  }, []);

  function startEdit(row: ShopifyPartner) {
    setEditingId(row.id);
    setEditForm({
      display_name: row.display_name ?? row.shop_url,
      mcp_endpoint: row.mcp_endpoint,
      supported_capabilities: row.supported_capabilities,
      price_premium_percent: row.price_premium_percent,
      available_to_customize: row.available_to_customize,
    });
  }

  async function saveEdit() {
    if (!editingId) return;
    try {
      const res = await fetch(`/api/platform/shopify-partners/${editingId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(editForm),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error((d as { detail?: string }).detail || "Failed");
      }
      setEditingId(null);
      setEditForm({});
      fetchList();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Failed to save");
    }
  }

  function cancelEdit() {
    setEditingId(null);
    setEditForm({});
  }

  if (loading) return <p className="text-[rgb(var(--color-text-secondary))]">Loading...</p>;

  if (list.length === 0) {
    return (
      <div className="rounded-lg border border-[rgb(var(--color-border))] bg-[rgb(var(--color-surface))] p-8 text-center">
        <p className="text-[rgb(var(--color-text-secondary))] mb-4">No Shopify partners yet.</p>
        <Button asChild size="sm">
          <Link href="/platform/partners/shopify-new">Add Shopify partner</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="border border-[rgb(var(--color-border))] rounded-lg overflow-x-auto">
      <table className="w-full min-w-[800px]">
        <thead className="bg-[rgb(var(--color-surface))]">
          <tr>
            <th className="text-left px-4 py-2">Shop / Display</th>
            <th className="text-left px-4 py-2">MCP endpoint</th>
            <th className="text-left px-4 py-2">Premium %</th>
            <th className="text-left px-4 py-2">Customize</th>
            <th className="text-left px-4 py-2">Token</th>
            <th className="text-left px-4 py-2">Updated</th>
            <th className="w-28 px-4 py-2">Actions</th>
          </tr>
        </thead>
        <tbody>
          {list.map((row) => (
            <tr key={row.id} className="border-t border-[rgb(var(--color-border))]">
              {editingId === row.id ? (
                <>
                  <td className="px-4 py-2" colSpan={2}>
                    <div className="space-y-2">
                      <input
                        type="text"
                        value={editForm.display_name ?? ""}
                        onChange={(e) => setEditForm((f) => ({ ...f, display_name: e.target.value }))}
                        placeholder="Display name"
                        className="w-full max-w-xs px-2 py-1.5 rounded border border-[rgb(var(--color-border))] text-sm"
                      />
                      <input
                        type="url"
                        value={editForm.mcp_endpoint ?? ""}
                        onChange={(e) => setEditForm((f) => ({ ...f, mcp_endpoint: e.target.value }))}
                        placeholder="MCP endpoint"
                        className="w-full max-w-md px-2 py-1.5 rounded border border-[rgb(var(--color-border))] text-sm"
                      />
                    </div>
                  </td>
                  <td className="px-4 py-2">
                    <input
                      type="number"
                      min={0}
                      step={0.01}
                      value={editForm.price_premium_percent ?? 0}
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
                        checked={editForm.available_to_customize ?? false}
                        onChange={(e) =>
                          setEditForm((f) => ({ ...f, available_to_customize: e.target.checked }))
                        }
                        className="rounded"
                      />
                      <span className="text-sm">Yes</span>
                    </label>
                  </td>
                  <td className="px-4 py-2" colSpan={2}>
                    {row.access_token_vault_ref ? (
                      <span className="text-xs text-green-600 dark:text-green-400">Set</span>
                    ) : (
                      <span className="text-xs text-[rgb(var(--color-text-secondary))]">—</span>
                    )}
                  </td>
                  <td className="px-4 py-2">
                    <div className="flex gap-1">
                      <Button size="sm" onClick={saveEdit}>
                        Save
                      </Button>
                      <Button size="sm" variant="outline" onClick={cancelEdit}>
                        Cancel
                      </Button>
                    </div>
                  </td>
                </>
              ) : (
                <>
                  <td className="px-4 py-2">
                    <div>
                      <div className="font-medium">{row.display_name || row.shop_url}</div>
                      <div className="text-xs text-[rgb(var(--color-text-secondary))] font-mono">
                        {row.shop_url}
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-2 font-mono text-xs max-w-[200px] truncate" title={row.mcp_endpoint}>
                    {row.mcp_endpoint}
                  </td>
                  <td className="px-4 py-2">{Number(row.price_premium_percent)}%</td>
                  <td className="px-4 py-2">
                    {row.available_to_customize ? (
                      <span className="text-green-600 dark:text-green-400">Yes</span>
                    ) : (
                      <span className="text-[rgb(var(--color-text-secondary))]">No</span>
                    )}
                  </td>
                  <td className="px-4 py-2">
                    {row.access_token_vault_ref ? (
                      <span className="text-xs text-green-600 dark:text-green-400">Set</span>
                    ) : (
                      <span className="text-xs text-[rgb(var(--color-text-secondary))]">—</span>
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
