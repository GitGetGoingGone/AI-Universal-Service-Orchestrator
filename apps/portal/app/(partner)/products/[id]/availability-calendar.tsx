"use client";

import { useEffect, useState } from "react";
import FullCalendar from "@fullcalendar/react";
import dayGridPlugin from "@fullcalendar/daygrid";
import timeGridPlugin from "@fullcalendar/timegrid";
import interactionPlugin from "@fullcalendar/interaction";
import type { EventChangeArg, EventClickArg, DateSelectArg } from "@fullcalendar/core";

type Slot = {
  id: string;
  start_at: string;
  end_at: string;
  booking_mode: string;
};

const MODE_COLORS: Record<string, string> = {
  auto_book: "#22c55e",
  check_before: "#f59e0b",
  not_available: "#6b7280",
};

const BOOKING_MODES = [
  { value: "auto_book", label: "Auto book", color: "#22c55e" },
  { value: "check_before", label: "Check before", color: "#f59e0b" },
  { value: "not_available", label: "Not available", color: "#6b7280" },
] as const;

export function AvailabilityCalendar({ productId }: { productId: string }) {
  const [events, setEvents] = useState<Slot[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedSlot, setSelectedSlot] = useState<{ id: string; start: string; end: string; mode: string } | null>(null);
  const [createMode, setCreateMode] = useState<"auto_book" | "check_before" | "not_available">("auto_book");

  async function fetchSlots() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/products/${productId}/availability`);
      if (!res.ok) throw new Error("Failed to load");
      const data = await res.json();
      setEvents(data.availability ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchSlots();
  }, [productId]);

  const fcEvents = events.map((s) => ({
    id: s.id,
    title: s.booking_mode === "auto_book" ? "Auto book" : s.booking_mode === "check_before" ? "Check before" : "Not available",
    start: s.start_at,
    end: s.end_at,
    backgroundColor: MODE_COLORS[s.booking_mode] ?? MODE_COLORS.auto_book,
  }));

  async function handleSelect(selectInfo: DateSelectArg) {
    try {
      const res = await fetch(`/api/products/${productId}/availability`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          start_at: selectInfo.startStr,
          end_at: selectInfo.endStr,
          booking_mode: createMode,
        }),
      });
      if (!res.ok) throw new Error("Failed to add");
      fetchSlots();
    } catch {
      setError("Failed to add slot");
    }
  }

  async function handleEventChange(changeInfo: EventChangeArg) {
    const id = changeInfo.event.id;
    try {
      const res = await fetch(`/api/products/${productId}/availability/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          start_at: changeInfo.event.startStr,
          end_at: changeInfo.event.endStr,
        }),
      });
      if (!res.ok) throw new Error("Failed to update");
      fetchSlots();
    } catch {
      setError("Failed to update");
      changeInfo.revert();
    }
  }

  function handleEventClick(clickInfo: EventClickArg) {
    const slot = events.find((s) => s.id === clickInfo.event.id);
    if (slot) {
      setSelectedSlot({
        id: slot.id,
        start: slot.start_at,
        end: slot.end_at,
        mode: slot.booking_mode,
      });
    }
  }

  async function changeSlotMode(mode: string) {
    if (!selectedSlot) return;
    try {
      const res = await fetch(`/api/products/${productId}/availability/${selectedSlot.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ booking_mode: mode }),
      });
      if (!res.ok) throw new Error("Failed");
      setSelectedSlot(null);
      fetchSlots();
    } catch {
      setError("Failed to update");
    }
  }

  async function deleteSlot() {
    if (!selectedSlot) return;
    if (!confirm("Delete this slot?")) return;
    try {
      const res = await fetch(`/api/products/${productId}/availability/${selectedSlot.id}`, {
        method: "DELETE",
      });
      if (!res.ok) throw new Error("Failed to delete");
      setSelectedSlot(null);
      fetchSlots();
    } catch {
      setError("Failed to delete");
    }
  }

  if (loading) return <p className="text-[rgb(var(--color-text-secondary))]">Loading calendar...</p>;
  if (error) return <p className="text-[rgb(var(--color-error))]">{error}</p>;

  return (
    <div className="mt-6">
      <div className="flex flex-wrap gap-4 items-center mb-2">
        <p className="text-sm text-[rgb(var(--color-text-secondary))]">
          Drag to create, drag to resize. Click event to change mode or delete.
        </p>
        <div className="flex items-center gap-2">
          <span className="text-sm">New slots:</span>
          {BOOKING_MODES.map((m) => (
            <button
              key={m.value}
              type="button"
              onClick={() => setCreateMode(m.value)}
              className={`px-2 py-1 rounded text-sm border-2 ${createMode === m.value ? "border-black dark:border-white" : "border-transparent opacity-70 hover:opacity-100"}`}
              style={{
                backgroundColor: m.color,
                color: m.value === "not_available" ? "#fff" : "#000",
              }}
            >
              {m.label}
            </button>
          ))}
        </div>
      </div>
      {selectedSlot && (
        <div className="mb-4 p-4 rounded-lg border border-[rgb(var(--color-border))] bg-[rgb(var(--color-surface))]">
          <p className="text-sm font-medium mb-2">
            Slot: {new Date(selectedSlot.start).toLocaleString()} – {new Date(selectedSlot.end).toLocaleTimeString()}
          </p>
          <p className="text-sm text-[rgb(var(--color-text-secondary))] mb-2">Change to:</p>
          <div className="flex flex-wrap gap-2">
            {BOOKING_MODES.map((m) => (
              <button
                key={m.value}
                type="button"
                onClick={() => changeSlotMode(m.value)}
                className={`px-3 py-1.5 rounded text-sm border-2 ${selectedSlot.mode === m.value ? "border-black dark:border-white" : "border-transparent opacity-80 hover:opacity-100"}`}
                style={{
                  backgroundColor: m.color,
                  color: m.value === "not_available" ? "#fff" : "#000",
                }}
              >
                {m.label}
              </button>
            ))}
            <button
              type="button"
              onClick={deleteSlot}
              className="px-3 py-1.5 rounded text-sm bg-red-500 text-white hover:bg-red-600"
            >
              Delete
            </button>
            <button
              type="button"
              onClick={() => setSelectedSlot(null)}
              className="px-3 py-1.5 rounded text-sm border border-[rgb(var(--color-border))]"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
      <FullCalendar
        plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin]}
        initialView="timeGridWeek"
        editable
        selectable
        selectMirror
        events={fcEvents}
        select={handleSelect}
        eventChange={handleEventChange}
        eventClick={handleEventClick}
        headerToolbar={{
          left: "prev,next today",
          center: "title",
          right: "dayGridMonth,timeGridWeek",
        }}
      />
    </div>
  );
}
