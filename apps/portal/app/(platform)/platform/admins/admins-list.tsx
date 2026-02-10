"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";

type Admin = {
  id: string;
  clerk_user_id: string | null;
  user_id: string | null;
  scope: string;
  created_at: string;
};

export function AdminsList() {
  const [admins, setAdmins] = useState<Admin[]>([]);
  const [loading, setLoading] = useState(true);
  const [clerkId, setClerkId] = useState("");
  const [adding, setAdding] = useState(false);

  async function fetchAdmins() {
    setLoading(true);
    try {
      const res = await fetch("/api/platform/admins");
      if (!res.ok) throw new Error("Failed");
      const data = await res.json();
      setAdmins(data.admins ?? []);
    } catch {
      setAdmins([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchAdmins();
  }, []);

  async function addAdmin() {
    if (!clerkId.trim()) return;
    setAdding(true);
    try {
      const res = await fetch("/api/platform/admins", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ clerk_user_id: clerkId.trim() }),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail || "Failed");
      }
      setClerkId("");
      fetchAdmins();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed");
    } finally {
      setAdding(false);
    }
  }

  async function removeAdmin(id: string) {
    if (!confirm("Remove this admin?")) return;
    try {
      const res = await fetch(`/api/platform/admins/${id}`, { method: "DELETE" });
      if (!res.ok) throw new Error("Failed");
      fetchAdmins();
    } catch {
      alert("Failed to remove");
    }
  }

  if (loading) return <p className="text-[rgb(var(--color-text-secondary))]">Loading...</p>;

  return (
    <div className="space-y-6">
      <div className="flex gap-2 flex-wrap items-end">
        <div>
          <label className="block text-sm font-medium mb-1">Clerk User ID</label>
          <input
            value={clerkId}
            onChange={(e) => setClerkId(e.target.value)}
            placeholder="user_2abc..."
            className="w-64 px-3 py-2 rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]"
          />
        </div>
        <Button onClick={addAdmin} disabled={adding}>
          {adding ? "Adding..." : "Add Admin"}
        </Button>
      </div>
      <p className="text-sm text-[rgb(var(--color-text-secondary))]">
        Get Clerk User ID from Clerk Dashboard → Users
      </p>

      <div className="border border-[rgb(var(--color-border))] rounded-lg overflow-hidden">
        <table className="w-full">
          <thead className="bg-[rgb(var(--color-surface))]">
            <tr>
              <th className="text-left px-4 py-2">Clerk User ID</th>
              <th className="text-left px-4 py-2">Scope</th>
              <th className="text-left px-4 py-2">Added</th>
              <th className="w-24 px-4 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {admins.map((a) => (
              <tr key={a.id} className="border-t border-[rgb(var(--color-border))]">
                <td className="px-4 py-2">{a.clerk_user_id || "—"}</td>
                <td className="px-4 py-2">{a.scope}</td>
                <td className="px-4 py-2">
                  {new Date(a.created_at).toLocaleDateString()}
                </td>
                <td className="px-4 py-2">
                  <Button
                    size="sm"
                    variant="destructive"
                    onClick={() => removeAdmin(a.id)}
                  >
                    Remove
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {admins.length === 0 && (
          <p className="px-4 py-8 text-center text-[rgb(var(--color-text-secondary))]">
            No platform admins yet.
          </p>
        )}
      </div>
    </div>
  );
}
