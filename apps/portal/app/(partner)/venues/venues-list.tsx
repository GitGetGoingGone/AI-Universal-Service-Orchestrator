"use client";

import { useEffect, useState } from "react";
import { PartnerGuard, PartnerRequiredMessage } from "@/components/partner-guard";
import { Button } from "@/components/ui/button";

type Venue = {
  id: string;
  name: string;
  address: Record<string, unknown> | null;
  timezone: string;
  is_active: boolean;
};

export function VenuesList() {
  const [venues, setVenues] = useState<Venue[]>([]);
  const [loading, setLoading] = useState(true);
  const [addOpen, setAddOpen] = useState(false);
  const [partnerRequired, setPartnerRequired] = useState(false);

  async function fetchVenues() {
    setLoading(true);
    setPartnerRequired(false);
    try {
      const res = await fetch("/api/venues");
      if (res.status === 403) {
        setPartnerRequired(true);
        return;
      }
      if (!res.ok) throw new Error("Failed");
      const data = await res.json();
      setVenues(data.venues ?? []);
    } catch {
      setVenues([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchVenues();
  }, []);

  async function deleteVenue(id: string) {
    if (!confirm("Delete this venue?")) return;
    try {
      const res = await fetch(`/api/venues/${id}`, { method: "DELETE" });
      if (!res.ok) throw new Error("Failed");
      fetchVenues();
    } catch {
      alert("Failed to delete");
    }
  }

  if (loading) return <p className="text-[rgb(var(--color-text-secondary))]">Loading...</p>;
  if (partnerRequired) return <PartnerRequiredMessage />;

  return (
    <PartnerGuard>
      <div className="space-y-4">
        <Button onClick={() => setAddOpen(true)}>Add Venue</Button>
        <div className="border border-[rgb(var(--color-border))] rounded-lg overflow-hidden">
          <table className="w-full">
            <thead className="bg-[rgb(var(--color-surface))]">
              <tr>
                <th className="text-left px-4 py-2">Name</th>
                <th className="text-left px-4 py-2">Address</th>
                <th className="text-left px-4 py-2">Timezone</th>
                <th className="text-left px-4 py-2">Active</th>
                <th className="w-24 px-4 py-2"></th>
              </tr>
            </thead>
            <tbody>
              {venues.map((v) => (
                <tr key={v.id} className="border-t border-[rgb(var(--color-border))]">
                  <td className="px-4 py-2">{v.name}</td>
                  <td className="px-4 py-2">
                    {v.address ? JSON.stringify(v.address) : "—"}
                  </td>
                  <td className="px-4 py-2">{v.timezone}</td>
                  <td className="px-4 py-2">{v.is_active ? "Yes" : "No"}</td>
                  <td className="px-4 py-2">
                    <Button size="sm" variant="destructive" onClick={() => deleteVenue(v.id)}>
                      Delete
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {venues.length === 0 && !addOpen && (
            <p className="px-4 py-8 text-center text-[rgb(var(--color-text-secondary))]">
              No venues. Add a location.
            </p>
          )}
        </div>
        {addOpen && (
          <AddVenueForm
            onClose={() => setAddOpen(false)}
            onSuccess={() => {
              setAddOpen(false);
              fetchVenues();
            }}
          />
        )}
      </div>
    </PartnerGuard>
  );
}

function AddVenueForm({
  onClose,
  onSuccess,
}: {
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [loading, setLoading] = useState(false);
  const [name, setName] = useState("");
  const [timezone, setTimezone] = useState("UTC");

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await fetch("/api/venues", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, timezone }),
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
        <h2 className="text-lg font-semibold mb-4">Add Venue</h2>
        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Name *</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              className="w-full px-3 py-2 rounded-md border border-[rgb(var(--color-border))]"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Timezone</label>
            <input
              value={timezone}
              onChange={(e) => setTimezone(e.target.value)}
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
