"use client";

import { useEffect, useState } from "react";

type Member = {
  id: string;
  email: string;
  display_name: string | null;
  role: string;
  is_active: boolean;
  invited_at: string;
  joined_at: string | null;
};

export default function TeamPage() {
  const [members, setMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(true);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("member");
  const [inviting, setInviting] = useState(false);

  const load = () => {
    fetch("/api/partners/team")
      .then((r) => r.json())
      .then((d) => {
        if (d.detail) throw new Error(d.detail);
        setMembers(d.members ?? []);
      })
      .catch(() => setMembers([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => load(), []);

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inviteEmail.trim()) return;
    setInviting(true);
    try {
      const res = await fetch("/api/partners/team", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: inviteEmail.trim(), role: inviteRole }),
      });
      const data = await res.json();
      if (res.ok) {
        setMembers((prev) => [data, ...prev]);
        setInviteEmail("");
        setInviteRole("member");
      } else {
        alert(data.detail ?? "Failed to invite");
      }
    } finally {
      setInviting(false);
    }
  };

  const handleRoleChange = async (id: string, role: string) => {
    const res = await fetch(`/api/partners/team/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role }),
    });
    if (res.ok) load();
  };

  const handleToggleActive = async (id: string, isActive: boolean) => {
    const res = await fetch(`/api/partners/team/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ is_active: isActive }),
    });
    if (res.ok) load();
  };

  const handleRemove = async (id: string) => {
    if (!confirm("Remove this member?")) return;
    const res = await fetch(`/api/partners/team/${id}`, { method: "DELETE" });
    if (res.ok) load();
  };

  if (loading) return <p className="p-6">Loading…</p>;

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Team</h1>

      <form onSubmit={handleInvite} className="flex gap-2 flex-wrap">
        <input
          type="email"
          placeholder="Email"
          value={inviteEmail}
          onChange={(e) => setInviteEmail(e.target.value)}
          className="rounded border border-[rgb(var(--color-border))] px-3 py-2 min-w-[200px]"
        />
        <select
          value={inviteRole}
          onChange={(e) => setInviteRole(e.target.value)}
          className="rounded border border-[rgb(var(--color-border))] px-3 py-2"
        >
          <option value="member">Member</option>
          <option value="admin">Admin</option>
          <option value="owner">Owner</option>
        </select>
        <button
          type="submit"
          disabled={inviting}
          className="px-4 py-2 rounded bg-[rgb(var(--color-primary))] text-white"
        >
          {inviting ? "Inviting…" : "Invite"}
        </button>
      </form>

      <div className="border border-[rgb(var(--color-border))] rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-[rgb(var(--color-surface))] border-b">
            <tr>
              <th className="text-left p-4">Email</th>
              <th className="text-left p-4">Name</th>
              <th className="text-left p-4">Role</th>
              <th className="text-left p-4">Status</th>
              <th className="text-left p-4">Invited</th>
              <th className="text-left p-4">Actions</th>
            </tr>
          </thead>
          <tbody>
            {members.map((m) => (
              <tr key={m.id} className="border-b border-[rgb(var(--color-border))] last:border-0">
                <td className="p-4">{m.email}</td>
                <td className="p-4">{m.display_name || "—"}</td>
                <td className="p-4">
                  <select
                    value={m.role}
                    onChange={(e) => handleRoleChange(m.id, e.target.value)}
                    className="rounded border border-[rgb(var(--color-border))] px-2 py-1 bg-transparent"
                  >
                    <option value="member">Member</option>
                    <option value="admin">Admin</option>
                    <option value="owner">Owner</option>
                  </select>
                </td>
                <td className="p-4">
                  <button
                    onClick={() => handleToggleActive(m.id, !m.is_active)}
                    className={`px-2 py-1 rounded text-xs ${m.is_active ? "bg-green-100 text-green-800" : "bg-gray-200 text-gray-600"}`}
                  >
                    {m.is_active ? "Active" : "Inactive"}
                  </button>
                </td>
                <td className="p-4">{new Date(m.invited_at).toLocaleDateString()}</td>
                <td className="p-4">
                  <button
                    onClick={() => handleRemove(m.id)}
                    className="text-red-600 text-sm hover:underline"
                  >
                    Remove
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {members.length === 0 && (
          <p className="p-6 text-[rgb(var(--color-text-secondary))]">No team members yet</p>
        )}
      </div>
    </div>
  );
}
