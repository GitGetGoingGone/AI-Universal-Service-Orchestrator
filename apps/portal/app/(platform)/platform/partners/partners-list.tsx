"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";

type Partner = {
  id: string;
  business_name: string;
  contact_email: string;
  business_type: string | null;
  verification_status: string;
  is_active?: boolean;
  created_at: string;
  chat_config?: { chat_widget_enabled?: boolean; admin_e2e_enabled?: boolean };
};

export function PartnersList() {
  const [partners, setPartners] = useState<Partner[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"all" | "pending" | "approved">("all");

  async function fetchPartners() {
    setLoading(true);
    try {
      const q = filter === "all" ? "" : `?status=${filter}`;
      const res = await fetch(`/api/platform/partners${q}`);
      if (!res.ok) throw new Error("Failed to load");
      const data = await res.json();
      setPartners(data.partners ?? []);
    } catch (err) {
      setPartners([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchPartners();
  }, [filter]);

  async function approve(id: string) {
    try {
      const res = await fetch(`/api/platform/partners/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ verification_status: "approved" }),
      });
      if (!res.ok) throw new Error("Failed");
      fetchPartners();
    } catch {
      alert("Failed to approve");
    }
  }

  async function reject(id: string) {
    try {
      const res = await fetch(`/api/platform/partners/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ verification_status: "rejected" }),
      });
      if (!res.ok) throw new Error("Failed");
      fetchPartners();
    } catch {
      alert("Failed to reject");
    }
  }

  async function remove(id: string) {
    if (!confirm("Remove this business? They will be marked as inactive but remain visible for record-keeping."))
      return;
    try {
      const res = await fetch(`/api/platform/partners/${id}`, { method: "DELETE" });
      if (!res.ok) throw new Error("Failed");
      fetchPartners();
    } catch {
      alert("Failed to remove");
    }
  }

  async function restore(id: string) {
    try {
      const res = await fetch(`/api/platform/partners/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ is_active: true }),
      });
      if (!res.ok) throw new Error("Failed");
      fetchPartners();
    } catch {
      alert("Failed to restore");
    }
  }

  async function toggleChatConfig(id: string, field: "chat_widget_enabled" | "admin_e2e_enabled", value: boolean) {
    try {
      const res = await fetch(`/api/platform/partners/${id}/chat-config`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ [field]: value }),
      });
      if (!res.ok) throw new Error("Failed");
      setPartners((prev) =>
        prev.map((p) =>
          p.id === id
            ? {
                ...p,
                chat_config: {
                  ...p.chat_config,
                  [field]: value,
                },
              }
            : p
        )
      );
    } catch {
      alert("Failed to update chat config");
    }
  }

  if (loading) return <p className="text-[rgb(var(--color-text-secondary))]">Loading...</p>;

  const pending = partners.filter((p) => p.verification_status === "pending");

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        {(["all", "pending", "approved"] as const).map((f) => (
          <Button
            key={f}
            variant={filter === f ? "default" : "outline"}
            size="sm"
            onClick={() => setFilter(f)}
          >
            {f === "all" ? "All" : f === "pending" ? "Pending" : "Approved"}
          </Button>
        ))}
      </div>

      <div className="border border-[rgb(var(--color-border))] rounded-lg overflow-hidden">
        <table className="w-full">
          <thead className="bg-[rgb(var(--color-surface))]">
            <tr>
              <th className="text-left px-4 py-2">Business</th>
              <th className="text-left px-4 py-2">Email</th>
              <th className="text-left px-4 py-2">Type</th>
              <th className="text-left px-4 py-2">Status</th>
              <th className="text-left px-4 py-2">Active</th>
              <th className="text-left px-4 py-2">Chat</th>
              <th className="text-left px-4 py-2">E2E</th>
              <th className="text-left px-4 py-2">Created</th>
              <th className="w-48 px-4 py-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {partners.map((p) => (
              <tr key={p.id} className="border-t border-[rgb(var(--color-border))]">
                <td className="px-4 py-2">{p.business_name}</td>
                <td className="px-4 py-2">{p.contact_email}</td>
                <td className="px-4 py-2">{p.business_type || "—"}</td>
                <td className="px-4 py-2">
                  <span
                    className={
                      p.verification_status === "pending"
                        ? "text-amber-600"
                        : p.verification_status === "approved"
                          ? "text-green-600"
                          : "text-red-600"
                    }
                  >
                    {p.verification_status}
                  </span>
                </td>
                <td className="px-4 py-2">
                  {p.is_active === false ? (
                    <span className="text-red-600">Removed</span>
                  ) : (
                    <span className="text-green-600">Yes</span>
                  )}
                </td>
                <td className="px-4 py-2">
                  <label className="flex items-center gap-1 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={p.chat_config?.chat_widget_enabled !== false}
                      onChange={(e) => toggleChatConfig(p.id, "chat_widget_enabled", e.target.checked)}
                      className="rounded"
                    />
                    <span className="text-sm">On</span>
                  </label>
                </td>
                <td className="px-4 py-2">
                  <label className="flex items-center gap-1 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={p.chat_config?.admin_e2e_enabled !== false}
                      onChange={(e) => toggleChatConfig(p.id, "admin_e2e_enabled", e.target.checked)}
                      className="rounded"
                    />
                    <span className="text-sm">On</span>
                  </label>
                </td>
                <td className="px-4 py-2">
                  {new Date(p.created_at).toLocaleDateString()}
                </td>
                <td className="px-4 py-2">
                  <div className="flex flex-wrap gap-2">
                    {p.verification_status === "pending" && (
                      <>
                        <Button size="sm" onClick={() => approve(p.id)}>
                          Approve
                        </Button>
                        <Button size="sm" variant="destructive" onClick={() => reject(p.id)}>
                          Reject
                        </Button>
                      </>
                    )}
                    {p.is_active === false ? (
                      <Button size="sm" variant="outline" onClick={() => restore(p.id)}>
                        Restore
                      </Button>
                    ) : (
                      <Button
                        size="sm"
                        variant="outline"
                        className="text-[rgb(var(--color-text-secondary))]"
                        onClick={() => remove(p.id)}
                        title="Mark as inactive"
                      >
                        Remove
                      </Button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {partners.length === 0 && (
          <p className="px-4 py-8 text-center text-[rgb(var(--color-text-secondary))]">
            No partners found.
          </p>
        )}
      </div>

      {filter === "all" && pending.length > 0 && (
        <p className="text-sm text-[rgb(var(--color-text-secondary))]">
          {pending.length} pending approval
        </p>
      )}
    </div>
  );
}
