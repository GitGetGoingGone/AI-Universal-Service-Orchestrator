"use client";

import { useState, useCallback, useRef, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { ChatPage } from "@/components/ChatPage";
import { LandingHero } from "@/components/LandingHero";
import { ExamplePrompts } from "@/components/ExamplePrompts";

function PageContent() {
  const [promptToSend, setPromptToSend] = useState<string | undefined>();
  const chatSectionRef = useRef<HTMLDivElement>(null);
  const searchParams = useSearchParams();

  const paymentSuccessOrderId =
    searchParams.get("payment_success") === "1"
      ? searchParams.get("order_id")
      : null;

  const handlePromptSelect = useCallback((prompt: string) => {
    setPromptToSend(prompt);
    chatSectionRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

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
    <div className="min-h-screen flex flex-col">
      <LandingHero />
      <ExamplePrompts onSelect={handlePromptSelect} />
      <div
        id="chat-section"
        ref={chatSectionRef}
        className="flex-1 px-4 pb-8 pt-4"
      >
        <div className="mx-auto max-w-3xl">
          <ChatPage
            promptToSend={promptToSend}
            onPromptSent={handlePromptSent}
            embeddedInLanding
            paymentSuccessOrderId={paymentSuccessOrderId}
            onPaymentSuccessHandled={handlePaymentSuccessHandled}
          />
        </div>
      </div>
    </div>
  );
}

export default function Page() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center">Loading…</div>}>
      <PageContent />
    </Suspense>
  );
}
