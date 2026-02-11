"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { PartnerRequiredMessage } from "@/components/partner-guard";

type Rfp = {
  id: string;
  order_id: string;
  bundle_id: string;
  request_type: string;
  title: string;
  description: string;
  deadline: string;
  compensation_cents: number;
  status: string;
};

export function RfpsList() {
  const [rfps, setRfps] = useState<Rfp[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [bidding, setBidding] = useState<string | null>(null);
  const [bidAmount, setBidAmount] = useState<Record<string, string>>({});
  const [capacityForm, setCapacityForm] = useState(false);
  const [capacity, setCapacity] = useState({ available_from: "", available_until: "", capacity_slots: 10 });

  async function fetchRfps() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/rfps?status=open");
      if (res.status === 403) {
        setError("PARTNER_REQUIRED");
        return;
      }
      if (res.status === 503) {
        const data = await res.json().catch(() => ({}));
        setError(data.detail || "Hub negotiator not configured");
        return;
      }
      if (!res.ok) throw new Error("Failed");
      const data = await res.json();
      setRfps(data.rfps ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchRfps();
  }, []);

  async function submitBid(rfpId: string) {
    const amount = parseInt(bidAmount[rfpId] || "0", 10);
    if (!amount || amount < 0) {
      setError("Enter valid amount (cents)");
      return;
    }
    setBidding(rfpId);
    setError(null);
    try {
      const res = await fetch(`/api/rfps/${rfpId}/bid`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ amount_cents: amount }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Bid failed");
      }
      fetchRfps();
      setBidAmount((prev) => ({ ...prev, [rfpId]: "" }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    } finally {
      setBidding(null);
    }
  }

  async function addCapacity() {
    if (!capacity.available_from || !capacity.available_until) {
      setError("From and until dates required");
      return;
    }
    setError(null);
    try {
      const res = await fetch("/api/rfps/capacity", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(capacity),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed");
      }
      setCapacityForm(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    }
  }

  if (loading) return <p className="text-[rgb(var(--color-text-secondary))]">Loading...</p>;
  if (error === "PARTNER_REQUIRED") return <PartnerRequiredMessage />;
  if (error) return <p className="text-[rgb(var(--color-error))]">{error}</p>;

  return (
    <div className="space-y-6">
      <div>
        <Button variant="outline" onClick={() => setCapacityForm(!capacityForm)}>
          {capacityForm ? "Cancel" : "Add Hub Capacity"}
        </Button>
        {capacityForm && (
          <div className="mt-4 p-4 rounded border border-[rgb(var(--color-border))] space-y-2">
            <input
              type="datetime-local"
              placeholder="Available from"
              value={capacity.available_from}
              onChange={(e) => setCapacity((p) => ({ ...p, available_from: e.target.value }))}
              className="rounded border px-2 py-1 mr-2"
            />
            <input
              type="datetime-local"
              placeholder="Available until"
              value={capacity.available_until}
              onChange={(e) => setCapacity((p) => ({ ...p, available_until: e.target.value }))}
              className="rounded border px-2 py-1 mr-2"
            />
            <input
              type="number"
              placeholder="Slots"
              value={capacity.capacity_slots}
              onChange={(e) => setCapacity((p) => ({ ...p, capacity_slots: parseInt(e.target.value, 10) || 0 }))}
              className="rounded border px-2 py-1 w-20"
            />
            <Button size="sm" onClick={addCapacity}>Add</Button>
          </div>
        )}
      </div>

      {rfps.length === 0 ? (
        <p className="text-[rgb(var(--color-text-secondary))]">No open RFPs.</p>
      ) : (
        <div className="space-y-4">
          {rfps.map((rfp) => (
            <div
              key={rfp.id}
              className="rounded-lg border border-[rgb(var(--color-border))] p-4 bg-[rgb(var(--color-surface))]"
            >
              <p className="font-medium">{rfp.title}</p>
              <p className="text-sm text-[rgb(var(--color-text-secondary))]">{rfp.description}</p>
              <p className="text-sm mt-2">
                Compensation: ${((rfp.compensation_cents || 0) / 100).toFixed(2)} • Deadline: {new Date(rfp.deadline).toLocaleString()}
              </p>
              <div className="mt-3 flex gap-2 items-center">
                <input
                  type="number"
                  placeholder="Bid amount (cents)"
                  value={bidAmount[rfp.id] ?? ""}
                  onChange={(e) => setBidAmount((p) => ({ ...p, [rfp.id]: e.target.value }))}
                  className="rounded border px-2 py-1 w-32"
                />
                <Button size="sm" onClick={() => submitBid(rfp.id)} disabled={!!bidding}>
                  {bidding === rfp.id ? "Submitting…" : "Submit Bid"}
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
