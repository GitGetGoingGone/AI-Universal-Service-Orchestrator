"use client";

import { useSearchParams } from "next/navigation";
import Link from "next/link";

export default function PaySuccessPage() {
  const searchParams = useSearchParams();
  const orderId = searchParams.get("order_id");

  return (
    <div className="p-6 max-w-md space-y-4">
      <h1 className="text-xl font-bold text-green-600">Payment successful</h1>
      <p className="text-[rgb(var(--color-text-secondary))]">
        {orderId
          ? `Order ${orderId.slice(0, 8)}... has been paid.`
          : "Your payment was successful."}
      </p>
      <div className="pt-4 border-t border-[rgb(var(--color-border))]">
        <Link
          href="/orders"
          className="inline-block px-4 py-2 rounded bg-[rgb(var(--color-primary))] text-white font-medium"
        >
          View orders
        </Link>
      </div>
    </div>
  );
}
