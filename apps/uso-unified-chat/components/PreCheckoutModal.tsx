"use client";

import { SignInButton } from "@clerk/nextjs";
import { hasClerk } from "@/components/AuthWrapper";

export type PreCheckoutModalProps = {
  orderId: string;
  onClose: () => void;
  onSignIn: () => void;
  onContinueWithPhone: () => void;
};

export function PreCheckoutModal({
  onClose,
  onSignIn,
  onContinueWithPhone,
}: PreCheckoutModalProps) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        className="max-w-md w-full rounded-xl bg-[var(--card)] p-6 border border-[var(--border)]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold">Before checkout</h2>
          <button
            onClick={onClose}
            className="text-[var(--muted)] hover:text-[var(--foreground)] text-xl leading-none"
            aria-label="Close"
          >
            ×
          </button>
        </div>
        <p className="text-sm text-[var(--muted)] mb-6">
          Sign in to save your order and conversation history — access them from any device.
        </p>
        <div className="space-y-3">
          {hasClerk && (
            <SignInButton mode="modal">
              <button
                type="button"
                onClick={onSignIn}
                className="w-full px-4 py-3 rounded-xl bg-[var(--primary-color)] text-[var(--primary-foreground)] font-medium hover:opacity-90"
              >
                Sign in
              </button>
            </SignInButton>
          )}
          <button
            type="button"
            onClick={onContinueWithPhone}
            className="w-full px-4 py-3 rounded-xl border border-[var(--border)] bg-[var(--card)] text-[var(--card-foreground)] font-medium hover:bg-[var(--border)]/20"
          >
            Continue with phone number
          </button>
        </div>
      </div>
    </div>
  );
}
