"use client";

import { useEffect, useRef } from "react";
import * as AdaptiveCards from "adaptivecards";
import "adaptivecards/dist/adaptivecards.css";

const darkHostConfig = new AdaptiveCards.HostConfig({
  actions: {
    actionsOrientation: AdaptiveCards.Enums.Orientation.Vertical,
  },
  containerStyles: {
    default: {
      backgroundColor: "#1e293b",
      foregroundColors: {
        default: { default: "#f8fafc", subtle: "#94a3b8" },
        dark: { default: "#f8fafc", subtle: "#94a3b8" },
        light: { default: "#0f172a", subtle: "#334155" },
        accent: { default: "#f59e0b", subtle: "#fbbf24" },
        attention: { default: "#ef4444", subtle: "#f87171" },
        good: { default: "#22c55e", subtle: "#4ade80" },
        warning: { default: "#eab308", subtle: "#facc15" },
      },
    },
    emphasis: {
      backgroundColor: "#334155",
      foregroundColors: {
        default: { default: "#f8fafc", subtle: "#94a3b8" },
        dark: { default: "#f8fafc", subtle: "#94a3b8" },
        light: { default: "#0f172a", subtle: "#334155" },
        accent: { default: "#f59e0b", subtle: "#fbbf24" },
        attention: { default: "#ef4444", subtle: "#f87171" },
        good: { default: "#22c55e", subtle: "#4ade80" },
        warning: { default: "#eab308", subtle: "#facc15" },
      },
    },
    accent: {
      backgroundColor: "#334155",
      foregroundColors: {
        default: { default: "#f8fafc", subtle: "#94a3b8" },
        dark: { default: "#f8fafc", subtle: "#94a3b8" },
        light: { default: "#0f172a", subtle: "#334155" },
        accent: { default: "#f59e0b", subtle: "#fbbf24" },
        attention: { default: "#ef4444", subtle: "#f87171" },
        good: { default: "#22c55e", subtle: "#4ade80" },
        warning: { default: "#eab308", subtle: "#facc15" },
      },
    },
    good: {
      backgroundColor: "#1e293b",
      foregroundColors: {
        default: { default: "#f8fafc", subtle: "#94a3b8" },
        dark: { default: "#f8fafc", subtle: "#94a3b8" },
        light: { default: "#0f172a", subtle: "#334155" },
        accent: { default: "#f59e0b", subtle: "#fbbf24" },
        attention: { default: "#ef4444", subtle: "#f87171" },
        good: { default: "#22c55e", subtle: "#4ade80" },
        warning: { default: "#eab308", subtle: "#facc15" },
      },
    },
    attention: {
      backgroundColor: "#1e293b",
      foregroundColors: {
        default: { default: "#f8fafc", subtle: "#94a3b8" },
        dark: { default: "#f8fafc", subtle: "#94a3b8" },
        light: { default: "#0f172a", subtle: "#334155" },
        accent: { default: "#f59e0b", subtle: "#fbbf24" },
        attention: { default: "#ef4444", subtle: "#f87171" },
        good: { default: "#22c55e", subtle: "#4ade80" },
        warning: { default: "#eab308", subtle: "#facc15" },
      },
    },
    warning: {
      backgroundColor: "#1e293b",
      foregroundColors: {
        default: { default: "#f8fafc", subtle: "#94a3b8" },
        dark: { default: "#f8fafc", subtle: "#94a3b8" },
        light: { default: "#0f172a", subtle: "#334155" },
        accent: { default: "#f59e0b", subtle: "#fbbf24" },
        attention: { default: "#ef4444", subtle: "#f87171" },
        good: { default: "#22c55e", subtle: "#4ade80" },
        warning: { default: "#eab308", subtle: "#facc15" },
      },
    },
  },
});

export type ActionPayload = {
  action?: string;
  product_id?: string;
  bundle_id?: string;
  item_id?: string;
  order_id?: string;
  standing_intent_id?: string;
  approved?: boolean;
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
    adaptiveCard.hostConfig = darkHostConfig;

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
