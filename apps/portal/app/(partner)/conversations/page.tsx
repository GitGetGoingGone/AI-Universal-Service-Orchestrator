"use client";

import Link from "next/link";
import { MessageCircle, UserCheck } from "lucide-react";

export default function ConversationsPage() {
  return (
    <div className="flex-1 flex flex-col items-center justify-center p-8 min-h-0">
      <div className="max-w-md w-full text-center space-y-6">
        <div className="flex justify-center">
          <div className="rounded-full bg-[rgb(var(--color-primary))]/10 p-4">
            <MessageCircle className="size-12 text-[rgb(var(--color-primary))]" aria-hidden />
          </div>
        </div>
        <h2 className="text-xl font-semibold text-[rgb(var(--color-text))]">
          Conversations
        </h2>
        <p className="text-sm text-[rgb(var(--color-text-secondary))]">
          Select a conversation from the sidebar to view and reply, or start a new one. Assign threads to your team so everyone knows who’s handling each customer.
        </p>
        <p className="text-sm text-[rgb(var(--color-text-secondary))]">
          Create a new conversation with the <strong>New conversation</strong> button in the sidebar.
        </p>
        <div className="flex flex-col sm:flex-row gap-3 justify-center pt-2">
          <Link
            href="/conversations?filter=unassigned"
            className="inline-flex items-center justify-center gap-2 px-4 py-3 rounded-lg bg-[rgb(var(--color-primary))] text-[rgb(var(--color-primary-foreground))] font-medium text-sm hover:opacity-90 transition-opacity focus:outline-none focus:ring-2 focus:ring-[rgb(var(--color-primary))] focus:ring-offset-2"
          >
            <UserCheck className="size-4" aria-hidden />
            View unassigned
          </Link>
          <Link
            href="/actions"
            className="inline-flex items-center justify-center gap-2 px-4 py-3 rounded-lg border border-[rgb(var(--color-border))] bg-[rgb(var(--color-surface))] text-[rgb(var(--color-text))] font-medium text-sm hover:bg-[rgb(var(--color-border))]/30 transition-colors focus:outline-none focus:ring-2 focus:ring-[rgb(var(--color-primary))] focus:ring-offset-2"
          >
            Actions
          </Link>
        </div>
        <p className="text-xs text-[rgb(var(--color-text-secondary))]/80 pt-4">
          From <Link href="/actions" className="text-[rgb(var(--color-primary))] hover:underline">Actions</Link> you can jump to unassigned conversations, pending tasks, and orders.
        </p>
      </div>
    </div>
  );
}
