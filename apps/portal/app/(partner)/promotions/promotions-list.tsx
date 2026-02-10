"use client";

import { useEffect, useState } from "react";
import { PartnerGuard, PartnerRequiredMessage } from "@/components/partner-guard";
import { Button } from "@/components/ui/button";

type Promotion = {
  id: string;
  name: string;
  promo_type: string;
  value: number | null;
  start_at: string;
  end_at: string;
  is_active: boolean;
};

export function PromotionsList() {
  const [promos, setPromos] = useState<Promotion[]>([]);
  const [loading, setLoading] = useState(true);
  const [addOpen, setAddOpen] = useState(false);
  const [partnerRequired, setPartnerRequired] = useState(false);

  async function fetchPromos() {
    setLoading(true);
    setPartnerRequired(false);
    try {
      const res = await fetch("/api/promotions");
      if (res.status === 403) {
        setPartnerRequired(true);
        return;
      }
      if (!res.ok) throw new Error("Failed");
      const data = await res.json();
      setPromos(data.promotions ?? []);
    } catch {
      setPromos([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchPromos();
  }, []);

  async function toggleActive(id: string, isActive: boolean) {
    try {
      const res = await fetch(`/api/promotions/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ is_active: !isActive }),
      });
      if (!res.ok) throw new Error("Failed");
      fetchPromos();
    } catch {
      alert("Failed to update");
    }
  }

  async function deletePromo(id: string) {
    if (!confirm("Delete this promotion?")) return;
    try {
      const res = await fetch(`/api/promotions/${id}`, { method: "DELETE" });
      if (!res.ok) throw new Error("Failed");
      fetchPromos();
    } catch {
      alert("Failed to delete");
    }
  }

  if (loading) return <p className="text-[rgb(var(--color-text-secondary))]">Loading...</p>;
  if (partnerRequired) return <PartnerRequiredMessage />;

  return (
    <PartnerGuard>
      <div className="space-y-4">
        <Button onClick={() => setAddOpen(true)}>Add Promotion</Button>
        <div className="border border-[rgb(var(--color-border))] rounded-lg overflow-hidden">
          <table className="w-full">
            <thead className="bg-[rgb(var(--color-surface))]">
              <tr>
                <th className="text-left px-4 py-2">Name</th>
                <th className="text-left px-4 py-2">Type</th>
                <th className="text-left px-4 py-2">Value</th>
                <th className="text-left px-4 py-2">Start</th>
                <th className="text-left px-4 py-2">End</th>
                <th className="text-left px-4 py-2">Active</th>
                <th className="w-24 px-4 py-2"></th>
              </tr>
            </thead>
            <tbody>
              {promos.map((p) => (
                <tr key={p.id} className="border-t border-[rgb(var(--color-border))]">
                  <td className="px-4 py-2">{p.name}</td>
                  <td className="px-4 py-2">{p.promo_type}</td>
                  <td className="px-4 py-2">{p.value != null ? p.value : "—"}</td>
                  <td className="px-4 py-2">
                    {new Date(p.start_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-2">
                    {new Date(p.end_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-2">
                    <input
                      type="checkbox"
                      checked={p.is_active}
                      onChange={() => toggleActive(p.id, p.is_active)}
                    />
                  </td>
                  <td className="px-4 py-2">
                    <Button size="sm" variant="destructive" onClick={() => deletePromo(p.id)}>
                      Delete
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {promos.length === 0 && !addOpen && (
            <p className="px-4 py-8 text-center text-[rgb(var(--color-text-secondary))]">
              No promotions. Add one to get started.
            </p>
          )}
        </div>
        {addOpen && (
          <AddPromotionForm
            onClose={() => setAddOpen(false)}
            onSuccess={() => {
              setAddOpen(false);
              fetchPromos();
            }}
          />
        )}
      </div>
    </PartnerGuard>
  );
}

function AddPromotionForm({
  onClose,
  onSuccess,
}: {
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    name: "",
    promo_type: "percent_off",
    value: "",
    start_at: new Date().toISOString().slice(0, 16),
    end_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().slice(0, 16),
  });

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await fetch("/api/promotions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: form.name,
          promo_type: form.promo_type,
          value: form.value ? Number(form.value) : null,
          start_at: new Date(form.start_at).toISOString(),
          end_at: new Date(form.end_at).toISOString(),
        }),
      });
      if (!res.ok) throw new Error("Failed");
      onSuccess();
    } catch {
      alert("Failed to add");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-[rgb(var(--color-background))] rounded-lg p-6 max-w-md w-full mx-4">
        <h2 className="text-lg font-semibold mb-4">Add Promotion</h2>
        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Name *</label>
            <input
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              required
              className="w-full px-3 py-2 rounded-md border border-[rgb(var(--color-border))]"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Type</label>
            <select
              value={form.promo_type}
              onChange={(e) => setForm((f) => ({ ...f, promo_type: e.target.value }))}
              className="w-full px-3 py-2 rounded-md border border-[rgb(var(--color-border))]"
            >
              <option value="percent_off">Percent off</option>
              <option value="fixed_off">Fixed amount off</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Value</label>
            <input
              type="number"
              step="0.01"
              value={form.value}
              onChange={(e) => setForm((f) => ({ ...f, value: e.target.value }))}
              placeholder="e.g. 10 for 10%"
              className="w-full px-3 py-2 rounded-md border border-[rgb(var(--color-border))]"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Start *</label>
            <input
              type="datetime-local"
              value={form.start_at}
              onChange={(e) => setForm((f) => ({ ...f, start_at: e.target.value }))}
              required
              className="w-full px-3 py-2 rounded-md border border-[rgb(var(--color-border))]"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">End *</label>
            <input
              type="datetime-local"
              value={form.end_at}
              onChange={(e) => setForm((f) => ({ ...f, end_at: e.target.value }))}
              required
              className="w-full px-3 py-2 rounded-md border border-[rgb(var(--color-border))]"
            />
          </div>
          <div className="flex gap-2 justify-end">
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? "Adding..." : "Add"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
