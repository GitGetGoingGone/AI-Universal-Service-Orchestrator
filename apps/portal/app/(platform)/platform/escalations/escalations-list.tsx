"use client";

import { useEffect, useState } from "react";

type Escalation = {
  id: string;
  conversation_ref: string;
  classification: string;
  status: string;
  assigned_to: string | null;
  assigned_to_clerk_id: string | null;
  created_at: string;
  resolved_at: string | null;
  resolution_notes: string | null;
};

export function EscalationsList({ clerkUserId }: { clerkUserId: string }) {
  const [escalations, setEscalations] = useState<Escalation[]>([]);
  const [statusFilter, setStatusFilter] = useState("pending");
  const [assigning, setAssigning] = useState<string | null>(null);
  const [resolving, setResolving] = useState<string | null>(null);
  const [resolveNotes, setResolveNotes] = useState<Record<string, string>>({});

  useEffect(() => {
    fetch(`/api/platform/escalations?status=${statusFilter}`)
      .then((res) => res.json())
      .then((data) => setEscalations(data.escalations || []))
      .catch(() => {});
  }, [statusFilter]);

  const handleAssign = async (id: string) => {
    setAssigning(id);
    try {
      const res = await fetch(`/api/platform/escalations/${id}/assign`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ assigned_to_clerk_id: clerkUserId }),
      });
      if (res.ok) {
        setEscalations((prev) =>
          prev.map((e) => (e.id === id ? { ...e, status: "assigned", assigned_to_clerk_id: clerkUserId } : e))
        );
      }
    } finally {
      setAssigning(null);
    }
  };

  const handleResolve = async (id: string) => {
    setResolving(id);
    const notes = resolveNotes[id] || "";
    try {
      const res = await fetch(`/api/platform/escalations/${id}/resolve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ resolution_notes: notes }),
      });
      if (res.ok) {
        setEscalations((prev) =>
          prev.map((e) =>
            e.id === id ? { ...e, status: "resolved", resolved_at: new Date().toISOString(), resolution_notes: notes } : e
          )
        );
        setResolveNotes((prev) => ({ ...prev, [id]: "" }));
      }
    } finally {
      setResolving(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex gap-2">
        {["pending", "assigned", "resolved"].map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`px-4 py-2 rounded capitalize ${
              statusFilter === s
                ? "bg-[rgb(var(--color-primary))] text-white"
                : "bg-[rgb(var(--color-surface))] border border-[rgb(var(--color-border))]"
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      <div className="border border-[rgb(var(--color-border))] rounded-lg overflow-hidden">
        {escalations.length === 0 ? (
          <p className="p-6 text-[rgb(var(--color-text-secondary))]">No escalations</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-[rgb(var(--color-surface))] border-b border-[rgb(var(--color-border))]">
              <tr>
                <th className="text-left p-4">Conversation</th>
                <th className="text-left p-4">Classification</th>
                <th className="text-left p-4">Status</th>
                <th className="text-left p-4">Created</th>
                <th className="text-left p-4">Actions</th>
              </tr>
            </thead>
            <tbody>
              {escalations.map((e) => (
                <tr key={e.id} className="border-b border-[rgb(var(--color-border))] last:border-0">
                  <td className="p-4">{e.conversation_ref}</td>
                  <td className="p-4">{e.classification}</td>
                  <td className="p-4">{e.status}</td>
                  <td className="p-4">{new Date(e.created_at).toLocaleString()}</td>
                  <td className="p-4">
                    <div className="flex flex-col gap-2">
                      {e.status === "pending" && (
                        <button
                          onClick={() => handleAssign(e.id)}
                          disabled={!!assigning}
                          className="text-sm text-amber-600 hover:underline"
                        >
                          {assigning === e.id ? "Assigning…" : "Assign to me"}
                        </button>
                      )}
                      {(e.status === "pending" || e.status === "assigned") && (
                        <>
                          <input
                            type="text"
                            placeholder="Resolution notes"
                            value={resolveNotes[e.id] || ""}
                            onChange={(ev) => setResolveNotes((prev) => ({ ...prev, [e.id]: ev.target.value }))}
                            className="rounded border border-[rgb(var(--color-border))] px-2 py-1 text-sm w-48"
                          />
                          <button
                            onClick={() => handleResolve(e.id)}
                            disabled={!!resolving}
                            className="text-sm text-green-600 hover:underline"
                          >
                            {resolving === e.id ? "Resolving…" : "Resolve"}
                          </button>
                        </>
                      )}
                      {e.status === "resolved" && e.resolution_notes && (
                        <span className="text-xs text-[rgb(var(--color-text-secondary))]">{e.resolution_notes}</span>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
