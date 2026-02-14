"use client";

import { useEffect, useRef } from "react";
import * as AdaptiveCards from "adaptivecards";
import "adaptivecards/dist/adaptivecards.css";

export type ActionPayload = {
  action?: string;
  product_id?: string;
  bundle_id?: string;
  item_id?: string;
  order_id?: string;
  [key: string]: unknown;
};

type AdaptiveCardRendererProps = {
  card: Record<string, unknown> | null;
  onAction?: (data: ActionPayload) => void;
  className?: string;
};

export function AdaptiveCardRenderer({
  card,
  onAction,
  className = "",
}: AdaptiveCardRendererProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!card || !containerRef.current) return;

    const adaptiveCard = new AdaptiveCards.AdaptiveCard();
    adaptiveCard.hostConfig = AdaptiveCards.defaultHostConfig;

    adaptiveCard.onExecuteAction = (action: AdaptiveCards.Action) => {
      const submitAction = action as AdaptiveCards.SubmitAction;
      const data = submitAction?.data as ActionPayload | undefined;
      if (data && onAction) {
        onAction(data);
      }
    };

    adaptiveCard.parse(card);
    const rendered = adaptiveCard.render();
    if (rendered) {
      containerRef.current.innerHTML = "";
      containerRef.current.appendChild(rendered);
    }

    return () => {
      containerRef.current?.replaceChildren();
    };
  }, [card, onAction]);

  if (!card) return null;

  return (
    <div
      ref={containerRef}
      className={`aco-adaptiveCard min-h-[60px] ${className}`}
    />
  );
}
