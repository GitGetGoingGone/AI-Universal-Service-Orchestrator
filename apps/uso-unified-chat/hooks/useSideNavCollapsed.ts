"use client";

import { useState, useEffect, useCallback } from "react";

const STORAGE_KEY = "uso_side_nav_collapsed";

export function useSideNavCollapsed() {
  const [collapsed, setCollapsedState] = useState(true);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(min-width: 768px)");
    const init = () => {
      if (mq.matches) {
        const stored = localStorage.getItem(STORAGE_KEY);
        setCollapsedState(stored === "true");
      } else {
        setCollapsedState(true);
      }
      setHydrated(true);
    };
    init();
    mq.addEventListener("change", init);
    return () => mq.removeEventListener("change", init);
  }, []);

  const setCollapsed = useCallback((value: boolean) => {
    setCollapsedState(value);
    if (typeof window !== "undefined") {
      localStorage.setItem(STORAGE_KEY, String(value));
    }
  }, []);

  const toggle = useCallback(() => {
    setCollapsedState((prev) => {
      const next = !prev;
      if (typeof window !== "undefined") {
        localStorage.setItem(STORAGE_KEY, String(next));
      }
      return next;
    });
  }, []);

  return { collapsed, setCollapsed, toggle, hydrated };
}
