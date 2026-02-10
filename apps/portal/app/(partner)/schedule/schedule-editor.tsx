"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { PartnerGuard, PartnerRequiredMessage } from "@/components/partner-guard";

const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

type Slot = { day_of_week: number; start_time: string; end_time: string };
type Product = { id: string; name: string };

export function ScheduleEditor() {
  const [slots, setSlots] = useState<Slot[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      fetch("/api/schedule").then(async (r) => {
        if (r.status === 403) return { _403: true };
        return r.json();
      }),
      fetch("/api/products").then(async (r) => {
        if (r.status === 403) return { _403: true };
        return r.json();
      }),
    ])
      .then(([scheduleData, productsData]) => {
        if ((scheduleData as { _403?: boolean })._403 || (productsData as { _403?: boolean })._403) {
          setError("PARTNER_REQUIRED");
          return;
        }
        const s = ((scheduleData as { schedule?: { day_of_week: number; start_time: string; end_time: string }[] }).schedule ?? []).map((x) => ({
          day_of_week: x.day_of_week,
          start_time: x.start_time?.slice(0, 5) || "09:00",
          end_time: x.end_time?.slice(0, 5) || "17:00",
        }));
        setSlots(s.length ? s : DAYS.map((_, i) => ({ day_of_week: i, start_time: "09:00", end_time: "17:00" })));
        setProducts(
          Array.isArray((productsData as { products?: { id: string; name: string }[] }).products)
            ? (productsData as { products: { id: string; name: string }[] }).products.map((p) => ({ id: p.id, name: p.name }))
            : []
        );
      })
      .catch(() => setError("Failed to load"))
      .finally(() => setLoading(false));
  }, []);

  function updateSlot(day: number, field: "start_time" | "end_time", value: string) {
    setSlots((prev) => {
      const exists = prev.find((s) => s.day_of_week === day);
      const base = exists ?? { day_of_week: day, start_time: "09:00", end_time: "17:00" };
      const updated = { ...base, [field]: value };
      const rest = prev.filter((s) => s.day_of_week !== day);
      return [...rest, updated].sort((a, b) => a.day_of_week - b.day_of_week);
    });
  }

  function toggleDay(day: number, enabled: boolean) {
    if (enabled) {
      const exists = slots.find((s) => s.day_of_week === day);
      if (!exists) {
        setSlots((prev) => [...prev, { day_of_week: day, start_time: "09:00", end_time: "17:00" }].sort((a, b) => a.day_of_week - b.day_of_week));
      }
    } else {
      setSlots((prev) => prev.filter((s) => s.day_of_week !== day));
    }
  }

  async function onSave() {
    setSaving(true);
    setError(null);
    try {
      const res = await fetch("/api/schedule", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ slots }),
      });
      if (!res.ok) throw new Error("Failed to save");
    } catch {
      setError("Failed to save");
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <p className="text-[rgb(var(--color-text-secondary))]">Loading...</p>;
  if (error === "PARTNER_REQUIRED") return <PartnerRequiredMessage />;
  if (error) return <p className="text-[rgb(var(--color-error))]">{error}</p>;

  return (
    <PartnerGuard>
    <div className="space-y-8">
      <section>
        <h2 className="font-semibold mb-2">Business Hours</h2>
        <p className="text-sm text-[rgb(var(--color-text-secondary))] mb-2">
          Default hours for your business. Per-product availability is below.
        </p>
    <div className="space-y-4 max-w-xl">
      <div className="border border-[rgb(var(--color-border))] rounded-lg overflow-hidden">
        <table className="w-full">
          <thead className="bg-[rgb(var(--color-surface))]">
            <tr>
              <th className="text-left px-4 py-2">Day</th>
              <th className="text-left px-4 py-2">Open</th>
              <th className="text-left px-4 py-2">Close</th>
            </tr>
          </thead>
          <tbody>
            {DAYS.map((name, day) => {
              const slot = slots.find((s) => s.day_of_week === day);
              const enabled = !!slot;
              return (
                <tr key={day} className="border-t border-[rgb(var(--color-border))]">
                  <td className="px-4 py-2">
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={enabled}
                        onChange={(e) => toggleDay(day, e.target.checked)}
                      />
                      {name}
                    </label>
                  </td>
                  <td className="px-4 py-2">
                    <input
                      type="time"
                      value={slot?.start_time ?? "09:00"}
                      disabled={!enabled}
                      onChange={(e) => updateSlot(day, "start_time", e.target.value)}
                      className="px-2 py-1 rounded border border-[rgb(var(--color-border))] disabled:opacity-50"
                    />
                  </td>
                  <td className="px-4 py-2">
                    <input
                      type="time"
                      value={slot?.end_time ?? "17:00"}
                      disabled={!enabled}
                      onChange={(e) => updateSlot(day, "end_time", e.target.value)}
                      className="px-2 py-1 rounded border border-[rgb(var(--color-border))] disabled:opacity-50"
                    />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <Button onClick={onSave} disabled={saving}>
        {saving ? "Saving..." : "Save Business Hours"}
      </Button>
    </div>
    </section>

    <section>
      <h2 className="font-semibold mb-2">Per-product availability</h2>
      <p className="text-sm text-[rgb(var(--color-text-secondary))] mb-2">
        Set when each product is available for booking. Click a product to edit its calendar.
      </p>
      {products.length === 0 ? (
        <p className="text-[rgb(var(--color-text-secondary))]">Add products first, then set their availability.</p>
      ) : (
        <ul className="space-y-2">
          {products.map((p) => (
            <li key={p.id}>
              <Link
                href={`/products/${p.id}`}
                className="text-[rgb(var(--color-primary))] hover:underline"
              >
                {p.name}
              </Link>
              <span className="text-[rgb(var(--color-text-secondary))] ml-2">→ Edit availability</span>
            </li>
          ))}
        </ul>
      )}
    </section>
    </div>
    </PartnerGuard>
  );
}
