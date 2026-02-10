"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

/** Shown when an API returns 403 (no partner). Use in lists that fetch before PartnerGuard can run. */
export function PartnerRequiredMessage() {
  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-950/30 p-6">
      <h2 className="font-semibold text-amber-800 dark:text-amber-200">Partner Account Required</h2>
      <p className="mt-2 text-amber-700 dark:text-amber-300">
        No partner account found. Use the same email as your registration, or contact support.
      </p>
      <p className="mt-2 text-sm">
        Sign in with the same email you used when registering, or{" "}
        <Link href="/register" className="text-[rgb(var(--color-primary))] hover:underline">
          register as a partner
        </Link>
        .
      </p>
    </div>
  );
}

type Props = {
  children: React.ReactNode;
  fallback?: React.ReactNode;
};

export function PartnerGuard({ children, fallback }: Props) {
  const [status, setStatus] = useState<"loading" | "approved" | "pending" | "none">("loading");
  const [message, setMessage] = useState<string>("");

  useEffect(() => {
    fetch("/api/partners/me")
      .then((res) => res.json())
      .then((data) => {
        if (data.partner?.verification_status === "approved") {
          setStatus("approved");
        } else if (data.partner?.verification_status === "pending") {
          setStatus("pending");
          setMessage(data.message || "Your application is pending approval.");
        } else {
          setStatus("none");
          setMessage(data.message || "No partner account found.");
        }
      })
      .catch(() => {
        setStatus("none");
        setMessage("Unable to verify partner status.");
      });
  }, []);

  if (status === "loading") {
    return fallback ?? <p className="text-[rgb(var(--color-text-secondary))]">Loading...</p>;
  }

  if (status === "approved") {
    return <>{children}</>;
  }

  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-950/30 p-6">
      <h2 className="font-semibold text-amber-800 dark:text-amber-200">
        {status === "pending" ? "Application Pending" : "Partner Account Required"}
      </h2>
      <p className="mt-2 text-amber-700 dark:text-amber-300">{message}</p>
      {status === "pending" && (
        <p className="mt-2 text-sm text-amber-600 dark:text-amber-400">
          A platform administrator will review your application. You will receive an email when approved.
        </p>
      )}
      {status === "none" && (
        <p className="mt-2 text-sm">
          Sign in with the same email you used when registering, or{" "}
          <Link href="/register" className="text-[rgb(var(--color-primary))] hover:underline">
            register as a partner
          </Link>
          .
        </p>
      )}
    </div>
  );
}
