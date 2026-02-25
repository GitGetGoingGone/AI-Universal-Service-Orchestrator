"use client";

import { createContext, useContext, useRef } from "react";

export type ActionPayload =
  | { action: "add_to_bundle"; product_id: string }
  | { action: "add_bundle_bulk"; product_ids: string[]; option_label?: string }
  | { action: "proceed_to_payment"; order_id?: string }
  | { action: "view_bundle"; bundle_id: string }
  | { action: "checkout"; bundle_id: string }
  | { action: "explore_product"; product_id: string; product_name?: string };

export type GatewayActionHandler = (payload: ActionPayload) => Promise<void>;

const GatewayActionContext = createContext<GatewayActionHandler | null>(null);

export function useGatewayAction(): GatewayActionHandler | null {
  return useContext(GatewayActionContext);
}

export function GatewayActionProvider({
  children,
  onAction,
}: {
  children: React.ReactNode;
  onAction: GatewayActionHandler;
}) {
  return (
    <GatewayActionContext.Provider value={onAction}>
      {children}
    </GatewayActionContext.Provider>
  );
}

