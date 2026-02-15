"use client";

import { useState, useCallback, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { ChatPage } from "@/components/ChatPage";

function PageContent() {
  const [promptToSend, setPromptToSend] = useState<string | undefined>();
  const searchParams = useSearchParams();

  const paymentSuccessOrderId =
    searchParams.get("payment_success") === "1"
      ? searchParams.get("order_id")
      : null;

  const handlePromptSent = useCallback(() => {
    setPromptToSend(undefined);
  }, []);

  const handlePaymentSuccessHandled = useCallback(() => {
    if (typeof window !== "undefined") {
      const url = new URL(window.location.href);
      url.searchParams.delete("payment_success");
      url.searchParams.delete("order_id");
      window.history.replaceState({}, "", url.pathname + url.search);
    }
  }, []);

  return (
    <ChatPage
      promptToSend={promptToSend}
      onPromptSent={handlePromptSent}
      showSideNav
      paymentSuccessOrderId={paymentSuccessOrderId}
      onPaymentSuccessHandled={handlePaymentSuccessHandled}
    />
  );
}

export default function Page() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center">Loading…</div>}>
      <PageContent />
    </Suspense>
  );
}
