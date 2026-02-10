"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/button";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-[rgb(var(--color-background))] px-4">
      <h1 className="text-xl font-semibold text-[rgb(var(--color-error))]">Something went wrong</h1>
      <p className="mt-2 text-[rgb(var(--color-text-secondary))] text-center">
        {error.message}
      </p>
      <Button onClick={reset} className="mt-6">
        Try again
      </Button>
    </div>
  );
}
