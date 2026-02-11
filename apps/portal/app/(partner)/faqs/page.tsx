"use client";

import { useEffect, useState } from "react";
import { PartnerGuard, PartnerRequiredMessage } from "@/components/partner-guard";
import { Button } from "@/components/ui/button";

type Faq = {
  id: string;
  question: string;
  answer: string;
  sort_order: number;
  is_active: boolean;
  created_at: string;
};

export default function FaqsPage() {
  const [faqs, setFaqs] = useState<Faq[]>([]);
  const [loading, setLoading] = useState(true);
  const [addOpen, setAddOpen] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [partnerRequired, setPartnerRequired] = useState(false);

  const load = () => {
    fetch("/api/partners/faqs")
      .then((r) => {
        if (r.status === 403) {
          setPartnerRequired(true);
          return { faqs: [] };
        }
        return r.json();
      })
      .then((d) => setFaqs(d.faqs ?? []))
      .catch(() => setFaqs([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => load(), []);

  if (loading) return <p className="p-6">Loading…</p>;
  if (partnerRequired) return <PartnerRequiredMessage />;

  return (
    <PartnerGuard>
      <div className="p-6 space-y-6">
        <div className="flex justify-between items-center">
          <h1 className="text-2xl font-bold">FAQs</h1>
          <Button onClick={() => setAddOpen(true)}>Add FAQ</Button>
        </div>
        <p className="text-sm text-[rgb(var(--color-text-secondary))]">
          Q&A pairs used by AI to answer common customer questions.
        </p>
        <div className="border border-[rgb(var(--color-border))] rounded-lg overflow-hidden">
          {faqs.length === 0 ? (
            <p className="p-6 text-[rgb(var(--color-text-secondary))]">No FAQs yet. Add one to get started.</p>
          ) : (
            <ul className="divide-y divide-[rgb(var(--color-border))]">
              {faqs.map((f) => (
                <li key={f.id} className="p-4">
                  <div className="flex justify-between items-start gap-4">
                    <div>
                      <p className="font-medium text-[rgb(var(--color-primary))]">Q: {f.question}</p>
                      <p className="text-sm mt-2">{f.answer}</p>
                    </div>
                    <div className="flex gap-2 shrink-0">
                      <Button size="sm" variant="outline" onClick={() => setEditId(f.id)}>
                        Edit
                      </Button>
                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={async () => {
                          if (!confirm("Delete this FAQ?")) return;
                          const res = await fetch(`/api/partners/faqs/${f.id}`, { method: "DELETE" });
                          if (res.ok) load();
                        }}
                      >
                        Delete
                      </Button>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
        {(addOpen || editId) && (
          <FaqForm
            faq={editId ? (faqs.find((f) => f.id === editId) ?? null) : null}
            onClose={() => {
              setAddOpen(false);
              setEditId(null);
            }}
            onSuccess={() => {
              setAddOpen(false);
              setEditId(null);
              load();
            }}
          />
        )}
      </div>
    </PartnerGuard>
  );
}

function FaqForm({
  faq,
  onClose,
  onSuccess,
}: {
  faq: Faq | null;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [question, setQuestion] = useState(faq?.question ?? "");
  const [answer, setAnswer] = useState(faq?.answer ?? "");
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim() || !answer.trim()) return;
    setSaving(true);
    try {
      const res = faq
        ? await fetch(`/api/partners/faqs/${faq.id}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question: question.trim(), answer: answer.trim() }),
          })
        : await fetch("/api/partners/faqs", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question: question.trim(), answer: answer.trim() }),
          });
      if (res.ok) onSuccess();
      else alert((await res.json()).detail ?? "Failed");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-[rgb(var(--color-background))] rounded-lg p-6 max-w-xl w-full mx-4">
        <h2 className="text-lg font-semibold mb-4">{faq ? "Edit FAQ" : "Add FAQ"}</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Question *</label>
            <input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              required
              className="w-full px-3 py-2 rounded border border-[rgb(var(--color-border))]"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Answer *</label>
            <textarea
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              required
              rows={4}
              className="w-full px-3 py-2 rounded border border-[rgb(var(--color-border))]"
            />
          </div>
          <div className="flex gap-2 justify-end">
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? "Saving…" : "Save"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
