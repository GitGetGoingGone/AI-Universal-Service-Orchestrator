"use client";

import { useEffect, useState } from "react";

type Review = {
  id: string;
  order_id: string;
  rating: number;
  comment: string | null;
  partner_response: string | null;
  responded_at: string | null;
  created_at: string;
};

type RatingsData = {
  avgRating: number;
  totalReviews: number;
  reviews: Review[];
};

export default function RatingsPage() {
  const [data, setData] = useState<RatingsData | null>(null);
  const [responding, setResponding] = useState<string | null>(null);
  const [responseText, setResponseText] = useState<Record<string, string>>({});

  useEffect(() => {
    fetch("/api/partners/ratings")
      .then((r) => r.json())
      .then((d) => {
        if (d.detail) throw new Error(d.detail);
        setData(d);
      })
      .catch(() => setData(null));
  }, []);

  const handleRespond = async (id: string) => {
    setResponding(id);
    try {
      const res = await fetch(`/api/partners/ratings/${id}/respond`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ partner_response: responseText[id] ?? "" }),
      });
      if (res.ok) {
        setData((prev) =>
          prev
            ? {
                ...prev,
                reviews: prev.reviews.map((r) =>
                  r.id === id
                    ? {
                        ...r,
                        partner_response: responseText[id] ?? "",
                        responded_at: new Date().toISOString(),
                      }
                    : r
                ),
              }
            : null
        );
        setResponseText((prev) => ({ ...prev, [id]: "" }));
      }
    } finally {
      setResponding(null);
    }
  };

  if (!data) return <p className="p-6">Loading…</p>;

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Ratings & Reviews</h1>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="p-6 rounded-lg bg-[rgb(var(--color-surface))] border border-[rgb(var(--color-border))]">
          <p className="text-[rgb(var(--color-text-secondary))]">Average Rating</p>
          <p className="text-3xl font-semibold">{data.avgRating.toFixed(1)} ★</p>
        </div>
        <div className="p-6 rounded-lg bg-[rgb(var(--color-surface))] border border-[rgb(var(--color-border))]">
          <p className="text-[rgb(var(--color-text-secondary))]">Total Reviews</p>
          <p className="text-3xl font-semibold">{data.totalReviews}</p>
        </div>
      </div>

      <div className="border border-[rgb(var(--color-border))] rounded-lg overflow-hidden">
        <h2 className="p-4 font-semibold bg-[rgb(var(--color-surface))]">Reviews</h2>
        {data.reviews.length === 0 ? (
          <p className="p-6 text-[rgb(var(--color-text-secondary))]">No reviews yet</p>
        ) : (
          <div className="divide-y divide-[rgb(var(--color-border))]">
            {data.reviews.map((r) => (
              <div key={r.id} className="p-4">
                <div className="flex justify-between items-start mb-2">
                  <span className="font-medium">
                    {"★".repeat(r.rating)}
                    {"☆".repeat(5 - r.rating)} Order {r.order_id?.slice(0, 8)}...
                  </span>
                  <span className="text-sm text-[rgb(var(--color-text-secondary))]">
                    {new Date(r.created_at).toLocaleDateString()}
                  </span>
                </div>
                {r.comment && <p className="text-sm mb-2">{r.comment}</p>}
                {r.partner_response ? (
                  <div className="mt-2 p-3 rounded bg-[rgb(var(--color-surface))] text-sm">
                    <p className="text-[rgb(var(--color-text-secondary))] text-xs">Your response</p>
                    <p>{r.partner_response}</p>
                  </div>
                ) : (
                  <div className="mt-2 flex gap-2">
                    <input
                      type="text"
                      placeholder="Respond to this review..."
                      value={responseText[r.id] ?? ""}
                      onChange={(e) =>
                        setResponseText((prev) => ({ ...prev, [r.id]: e.target.value }))
                      }
                      className="flex-1 rounded border border-[rgb(var(--color-border))] px-3 py-2 text-sm"
                    />
                    <button
                      onClick={() => handleRespond(r.id)}
                      disabled={!!responding}
                      className="px-4 py-2 rounded bg-[rgb(var(--color-primary))] text-white text-sm"
                    >
                      {responding === r.id ? "Sending…" : "Respond"}
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
