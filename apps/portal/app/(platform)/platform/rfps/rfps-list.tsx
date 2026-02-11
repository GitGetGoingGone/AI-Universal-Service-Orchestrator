"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";

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
  winning_bid_id?: string;
};

type Bid = {
  id: string;
  hub_partner_id: string;
  amount_cents: number;
  status: string;
};

export function PlatformRfpsList() {
  const [rfps, setRfps] = useState<Rfp[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [selecting, setSelecting] = useState<string | null>(null);
  const [newRfp, setNewRfp] = useState({
    title: "",
    description: "",
    request_type: "assembly",
    deadline: "",
    compensation_cents: 0,
    order_id: "",
    bundle_id: "",
  });

  async function fetchRfps() {
    setLoading(true);
    setError(null);
    try {
      const [openRes, closedRes] = await Promise.all([
        fetch("/api/platform/rfps?status=open"),
        fetch("/api/platform/rfps?status=closed"),
      ]);
      if (openRes.status === 403 || closedRes.status === 403) {
        setError("Platform admin required");
        return;
      }
      const openData = await openRes.json().catch(() => ({}));
      const closedData = await closedRes.json().catch(() => ({}));
      const open = openData.rfps ?? [];
      const closed = closedData.rfps ?? [];
      setRfps([...open, ...closed]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchRfps();
  }, []);

  async function createRfp() {
    if (!newRfp.deadline || !newRfp.title) {
      setError("Title and deadline required");
      return;
    }
    setCreating(true);
    setError(null);
    try {
      const res = await fetch("/api/platform/rfps", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newRfp),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed");
      }
      setNewRfp({ title: "", description: "", request_type: "assembly", deadline: "", compensation_cents: 0, order_id: "", bundle_id: "" });
      fetchRfps();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    } finally {
      setCreating(false);
    }
  }

  async function selectWinner(rfpId: string, bidId: string) {
    setSelecting(rfpId);
    setError(null);
    try {
      const res = await fetch(`/api/platform/rfps/${rfpId}/select-winner`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ bid_id: bidId }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed");
      }
      fetchRfps();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    } finally {
      setSelecting(null);
    }
  }

  if (loading) return <p className="text-[rgb(var(--color-text-secondary))]">Loading...</p>;
  if (error) return <p className="text-[rgb(var(--color-error))]">{error}</p>;

  return (
    <div className="space-y-6">
      <div className="p-4 rounded border border-[rgb(var(--color-border))] space-y-2">
        <h2 className="font-medium">Create RFP</h2>
        <input
          type="text"
          placeholder="Title"
          value={newRfp.title}
          onChange={(e) => setNewRfp((p) => ({ ...p, title: e.target.value }))}
          className="rounded border px-2 py-1 w-full max-w-md"
        />
        <input
          type="text"
          placeholder="Description"
          value={newRfp.description}
          onChange={(e) => setNewRfp((p) => ({ ...p, description: e.target.value }))}
          className="rounded border px-2 py-1 w-full max-w-md"
        />
        <input
          type="datetime-local"
          placeholder="Deadline"
          value={newRfp.deadline}
          onChange={(e) => setNewRfp((p) => ({ ...p, deadline: e.target.value }))}
          className="rounded border px-2 py-1"
        />
        <input
          type="number"
          placeholder="Compensation (cents)"
          value={newRfp.compensation_cents || ""}
          onChange={(e) => setNewRfp((p) => ({ ...p, compensation_cents: parseInt(e.target.value, 10) || 0 }))}
          className="rounded border px-2 py-1 w-32"
        />
        <input
          type="text"
          placeholder="Order ID (optional)"
          value={newRfp.order_id}
          onChange={(e) => setNewRfp((p) => ({ ...p, order_id: e.target.value }))}
          className="rounded border px-2 py-1 w-full max-w-md"
        />
        <input
          type="text"
          placeholder="Bundle ID (optional)"
          value={newRfp.bundle_id}
          onChange={(e) => setNewRfp((p) => ({ ...p, bundle_id: e.target.value }))}
          className="rounded border px-2 py-1 w-full max-w-md"
        />
        <Button onClick={createRfp} disabled={creating}>{creating ? "Creating…" : "Create RFP"}</Button>
      </div>

      <div className="space-y-4">
        {rfps.map((rfp) => (
          <RfpCard
            key={rfp.id}
            rfp={rfp}
            onSelectWinner={selectWinner}
            selecting={selecting === rfp.id}
          />
        ))}
      </div>
    </div>
  );
}

function RfpCard({ rfp, onSelectWinner, selecting }: { rfp: Rfp; onSelectWinner: (rfpId: string, bidId: string) => void; selecting: boolean }) {
  const [bids, setBids] = useState<Bid[]>([]);
  const [loadingBids, setLoadingBids] = useState(false);

  async function loadBids() {
    setLoadingBids(true);
    try {
      const res = await fetch(`/api/platform/rfps/${rfp.id}/bids`);
      const data = await res.json().catch(() => ({}));
      setBids(data.bids ?? []);
    } finally {
      setLoadingBids(false);
    }
  }

  useEffect(() => {
    if (rfp.status === "open") loadBids();
  }, [rfp.id, rfp.status]);

  return (
    <div className="rounded-lg border border-[rgb(var(--color-border))] p-4 bg-[rgb(var(--color-surface))]">
      <p className="font-medium">{rfp.title}</p>
      <p className="text-sm text-[rgb(var(--color-text-secondary))]">{rfp.description}</p>
      <p className="text-sm mt-2">
        Status: {rfp.status} • Compensation: ${((rfp.compensation_cents || 0) / 100).toFixed(2)} • Deadline: {new Date(rfp.deadline).toLocaleString()}
      </p>
      {rfp.status === "open" && (
        <div className="mt-3">
          {loadingBids ? (
            <p className="text-sm">Loading bids…</p>
          ) : bids.length === 0 ? (
            <p className="text-sm text-[rgb(var(--color-text-secondary))]">No bids yet</p>
          ) : (
            <div className="space-y-2">
              <p className="text-sm font-medium">Bids:</p>
              {bids.map((bid) => (
                <div key={bid.id} className="flex items-center gap-2">
                  <span className="text-sm">${(bid.amount_cents / 100).toFixed(2)} (Hub: {bid.hub_partner_id})</span>
                  <Button size="sm" onClick={() => onSelectWinner(rfp.id, bid.id)} disabled={selecting}>
                    {selecting ? "Selecting…" : "Select Winner"}
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
