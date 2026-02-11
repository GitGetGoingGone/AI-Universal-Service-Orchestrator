"use client";

import { useEffect, useState } from "react";
import { PartnerGuard, PartnerRequiredMessage } from "@/components/partner-guard";
import { Button } from "@/components/ui/button";

type Article = {
  id: string;
  title: string;
  content: string;
  sort_order: number;
  is_active: boolean;
  created_at: string;
};

export default function KnowledgeBasePage() {
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);
  const [addOpen, setAddOpen] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [partnerRequired, setPartnerRequired] = useState(false);

  const load = () => {
    fetch("/api/partners/knowledge-base")
      .then((r) => {
        if (r.status === 403) {
          setPartnerRequired(true);
          return { articles: [] };
        }
        return r.json();
      })
      .then((d) => setArticles(d.articles ?? []))
      .catch(() => setArticles([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => load(), []);

  if (loading) return <p className="p-6">Loading…</p>;
  if (partnerRequired) return <PartnerRequiredMessage />;

  return (
    <PartnerGuard>
      <div className="p-6 space-y-6">
        <div className="flex justify-between items-center">
          <h1 className="text-2xl font-bold">Knowledge Base</h1>
          <Button onClick={() => setAddOpen(true)}>Add Article</Button>
        </div>
        <p className="text-sm text-[rgb(var(--color-text-secondary))]">
          Articles used by AI to answer customer questions. Add policies, how-tos, and general info.
        </p>
        <div className="border border-[rgb(var(--color-border))] rounded-lg overflow-hidden">
          {articles.length === 0 ? (
            <p className="p-6 text-[rgb(var(--color-text-secondary))]">No articles yet. Add one to get started.</p>
          ) : (
            <ul className="divide-y divide-[rgb(var(--color-border))]">
              {articles.map((a) => (
                <li key={a.id} className="p-4">
                  <div className="flex justify-between items-start">
                    <div>
                      <h2 className="font-semibold">{a.title}</h2>
                      <p className="text-sm text-[rgb(var(--color-text-secondary))] mt-1 line-clamp-2">
                        {a.content}
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <Button size="sm" variant="outline" onClick={() => setEditId(a.id)}>
                        Edit
                      </Button>
                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={async () => {
                          if (!confirm("Delete this article?")) return;
                          const res = await fetch(`/api/partners/knowledge-base/${a.id}`, {
                            method: "DELETE",
                          });
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
          <ArticleForm
            article={editId ? (articles.find((a) => a.id === editId) ?? null) : null}
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

function ArticleForm({
  article,
  onClose,
  onSuccess,
}: {
  article: Article | null;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [title, setTitle] = useState(article?.title ?? "");
  const [content, setContent] = useState(article?.content ?? "");
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !content.trim()) return;
    setSaving(true);
    try {
      const res = article
        ? await fetch(`/api/partners/knowledge-base/${article.id}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ title: title.trim(), content: content.trim() }),
          })
        : await fetch("/api/partners/knowledge-base", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ title: title.trim(), content: content.trim() }),
          });
      if (res.ok) onSuccess();
      else alert((await res.json()).detail ?? "Failed");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-[rgb(var(--color-background))] rounded-lg p-6 max-w-xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <h2 className="text-lg font-semibold mb-4">{article ? "Edit Article" : "Add Article"}</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Title *</label>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
              className="w-full px-3 py-2 rounded border border-[rgb(var(--color-border))]"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Content *</label>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              required
              rows={8}
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
