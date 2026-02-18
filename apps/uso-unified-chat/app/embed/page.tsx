"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import dynamic from "next/dynamic";

const ChatPage = dynamic(
  () => import("@/components/ChatPage").then((m) => m.ChatPage),
  { ssr: false }
);

type EmbedConfig = {
  disabled?: boolean;
  message?: string;
  primary_color?: string;
  secondary_color?: string;
  font_family?: string;
  font_size_px?: number;
  welcome_message?: string;
  e2e_add_to_bundle?: boolean;
  e2e_checkout?: boolean;
  e2e_payment?: boolean;
  chat_typing_enabled?: boolean;
  chat_typing_speed_ms?: number;
};

function EmbedContent() {
  const searchParams = useSearchParams();
  const partnerId = searchParams.get("partner_id") || undefined;
  const parentOrigin = searchParams.get("parent_origin") || undefined;
  const [config, setConfig] = useState<EmbedConfig | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!partnerId) {
      setLoading(false);
      return;
    }
    const params = new URLSearchParams({ partner_id: partnerId });
    if (parentOrigin) params.set("parent_origin", parentOrigin);
    fetch(`/api/embed/config?${params}`)
      .then((r) => r.json())
      .then(setConfig)
      .catch(() => setConfig({ disabled: true }))
      .finally(() => setLoading(false));
  }, [partnerId, parentOrigin]);

  useEffect(() => {
    if (!config?.primary_color) return;
    document.documentElement.style.setProperty("--primary-color", config.primary_color);
    if (config.secondary_color) {
      document.documentElement.style.setProperty("--secondary-color", config.secondary_color);
    }
    if (config.font_family) {
      document.documentElement.style.setProperty("font-family", config.font_family);
    }
  }, [config]);

  if (loading && partnerId) {
    return (
      <div className="flex items-center justify-center h-screen bg-[var(--background)]">
        <div className="animate-pulse text-slate-400">Loading chat...</div>
      </div>
    );
  }

  if (config?.disabled) {
    return (
      <div className="flex items-center justify-center h-screen bg-[var(--background)]">
        <p className="text-slate-400">{config.message ?? "Chat unavailable"}</p>
      </div>
    );
  }

  const e2eEnabled =
    !config ||
    config.e2e_add_to_bundle !== false ||
    config.e2e_checkout !== false ||
    config.e2e_payment !== false;

  return (
    <div className="h-screen w-full min-h-[400px]">
      <ChatPage
        partnerId={partnerId}
        e2eEnabled={e2eEnabled ?? true}
        welcomeMessage={config?.welcome_message}
        chatConfig={{
          chat_typing_enabled: config?.chat_typing_enabled,
          chat_typing_speed_ms: config?.chat_typing_speed_ms,
          font_size_px: config?.font_size_px,
        }}
        embeddedInLanding
        showSideNav={false}
      />
    </div>
  );
}

export default function EmbedPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center h-screen bg-[var(--background)]">
          <div className="animate-pulse text-slate-400">Loading chat...</div>
        </div>
      }
    >
      <EmbedContent />
    </Suspense>
  );
}
