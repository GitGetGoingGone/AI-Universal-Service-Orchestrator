"use client";

import { useState } from "react";

export type FulfillmentFieldId = "pickup_time" | "pickup_address" | "delivery_address";

const FULFILLMENT_FIELD_CONFIG: Record<
  FulfillmentFieldId,
  { label: string; placeholder: string }
> = {
  pickup_time: { label: "Pickup time", placeholder: "e.g. 6:00 PM" },
  pickup_address: { label: "Pickup address", placeholder: "Street address for pickup" },
  delivery_address: { label: "Delivery address", placeholder: "Address for delivery (e.g. restaurant)" },
};

export type BundleFulfillmentModalProps = {
  optionLabel?: string;
  onClose: () => void;
  onSubmit: (details: Record<string, string>) => void;
  requiredFields?: string[];
  initialValues?: Record<string, string>;
};

export function BundleFulfillmentModal({
  optionLabel,
  onClose,
  onSubmit,
  requiredFields = ["pickup_time", "pickup_address", "delivery_address"],
  initialValues = {},
}: BundleFulfillmentModalProps) {
  const [values, setValues] = useState<Record<string, string>>(() => {
    const init: Record<string, string> = {};
    for (const f of requiredFields) {
      init[f] = initialValues[f] ?? "";
    }
    return init;
  });
  const [error, setError] = useState("");

  const handleChange = (field: string, value: string) => {
    setValues((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    const details: Record<string, string> = {};
    for (const f of requiredFields) {
      const v = (values[f] ?? "").trim();
      if (!v) {
        setError("Please fill in all required fields.");
        return;
      }
      details[f] = v;
    }
    onSubmit(details);
  };

  const fieldLabels = requiredFields
    .map((f) => FULFILLMENT_FIELD_CONFIG[f as FulfillmentFieldId]?.label ?? f)
    .join(", ");

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        className="max-w-md w-full rounded-xl bg-[var(--card)] p-6 border border-[var(--border)]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold">
            {optionLabel ? `Add ${optionLabel}` : "Complete your bundle"}
          </h2>
          <button
            onClick={onClose}
            className="text-[var(--muted)] hover:text-[var(--foreground)] text-xl leading-none"
            aria-label="Close"
          >
            ×
          </button>
        </div>
        <p className="text-sm text-[var(--muted)] mb-4">
          Please provide {fieldLabels} before adding this bundle.
        </p>
        <form onSubmit={handleSubmit} className="space-y-4">
          {requiredFields.map((fieldId) => {
            const cfg = FULFILLMENT_FIELD_CONFIG[fieldId as FulfillmentFieldId];
            return (
              <div key={fieldId}>
                <label htmlFor={fieldId} className="block text-sm font-medium mb-1">
                  {cfg?.label ?? fieldId} <span className="text-red-500">*</span>
                </label>
                <input
                  id={fieldId}
                  type="text"
                  placeholder={cfg?.placeholder ?? ""}
                  value={values[fieldId] ?? ""}
                  onChange={(e) => handleChange(fieldId, e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--background)] text-[var(--foreground)]"
                />
              </div>
            );
          })}
          {error && <p className="text-sm text-red-500">{error}</p>}
          <div className="flex gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 rounded-lg border border-[var(--border)] bg-[var(--card)] text-[var(--card-foreground)] font-medium"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="flex-1 px-4 py-2 rounded-lg bg-[var(--primary-color)] text-[var(--primary-foreground)] font-medium hover:opacity-90"
            >
              Add bundle
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
