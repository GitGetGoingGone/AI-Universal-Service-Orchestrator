"use client";

import { useState, useRef } from "react";
import { Button } from "@/components/ui/button";

type ImportSource = "shopify_csv";

const SOURCES: { value: ImportSource; label: string }[] = [
  { value: "shopify_csv", label: "Shopify CSV export" },
];

type Props = {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
};

type ImportResult = {
  created: number;
  failed: number;
  skipped: number;
  errors: { row: number; message: string }[];
  total_rows: number;
};

export function ImportProductsDialog({ open, onClose, onSuccess }: Props) {
  const [source, setSource] = useState<ImportSource>("shopify_csv");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!open) return null;

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const file = fileInputRef.current?.files?.[0];
    if (!file) {
      setError("Choose a CSV file");
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const formData = new FormData();
      formData.set("file", file);
      formData.set("source", source);

      const res = await fetch("/api/products/import", {
        method: "POST",
        body: formData,
      });
      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        setError(data.detail || "Import failed");
        return;
      }

      setResult({
        created: data.created ?? 0,
        failed: data.failed ?? 0,
        skipped: data.skipped ?? 0,
        errors: data.errors ?? [],
        total_rows: data.total_rows ?? 0,
      });
      if (data.created > 0) {
        onSuccess();
      }
    } catch {
      setError("Request failed");
    } finally {
      setLoading(false);
    }
  }

  function handleClose() {
    setError(null);
    setResult(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
    onClose();
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-[rgb(var(--color-background))] rounded-lg p-6 max-w-md w-full mx-4">
        <h2 className="text-lg font-semibold mb-2">Import products</h2>
        <p className="text-sm text-[rgb(var(--color-text-secondary))] mb-4">
          Upload a CSV in Shopify export format. More sources (e.g. WooCommerce, direct API) can be added later.
        </p>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Source</label>
            <select
              value={source}
              onChange={(e) => setSource(e.target.value as ImportSource)}
              className="w-full px-3 py-2 rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]"
            >
              {SOURCES.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">CSV file</label>
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,text/csv"
              className="w-full px-3 py-2 rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))] text-sm"
            />
            <p className="text-xs text-[rgb(var(--color-text-secondary))] mt-1">
              Use Shopify product export columns: Handle, Title, Body (HTML), Vendor, Type, Tags, Published, Variant Price, Image Src, etc.
            </p>
          </div>
          {error && <p className="text-sm text-[rgb(var(--color-error))]">{error}</p>}
          {result && (
            <div className="p-3 rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-surface))] text-sm space-y-1">
              <p>Created: {result.created} · Failed: {result.failed} · Skipped: {result.skipped}</p>
              {result.errors.length > 0 && (
                <ul className="list-disc ml-4 text-[rgb(var(--color-error))]">
                  {result.errors.slice(0, 5).map((e, i) => (
                    <li key={i}>Row {e.row}: {e.message}</li>
                  ))}
                  {result.errors.length > 5 && <li>… and {result.errors.length - 5} more</li>}
                </ul>
              )}
            </div>
          )}
          <div className="flex gap-2 justify-end">
            <Button type="button" variant="outline" onClick={handleClose}>
              {result ? "Close" : "Cancel"}
            </Button>
            {!result && (
              <Button type="submit" disabled={loading}>
                {loading ? "Importing…" : "Import"}
              </Button>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}
