"use client";

import { motion } from "framer-motion";

const CAPABILITIES = [
  {
    title: "Discover",
    description: "Search products in natural language. Say \"find roses\" or \"best chocolates for mom\".",
    icon: "🔍",
  },
  {
    title: "Bundle",
    description: "Add multiple items to one order. Plan a date night, anniversary gift, or event.",
    icon: "📦",
  },
  {
    title: "Checkout",
    description: "Complete your order and pay securely — no leaving the chat.",
    icon: "💳",
  },
  {
    title: "Reminders",
    description: "Set standing intents: \"Notify me when roses go on sale.\"",
    icon: "🔔",
  },
];

export function LandingHero() {
  return (
    <section className="relative overflow-hidden px-4 py-16 sm:py-24">
      {/* Subtle gradient background */}
      <div
        className="absolute inset-0 -z-10 opacity-30"
        style={{
          background: `radial-gradient(ellipse 80% 50% at 50% -20%, var(--primary-color), transparent)`,
        }}
      />

      <div className="mx-auto flex max-w-5xl flex-col gap-12 lg:flex-row lg:items-start lg:justify-between lg:gap-16">
        {/* Left: headline */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="flex-1 text-left lg:max-w-xl"
        >
          <h1 className="text-3xl font-bold tracking-tight sm:text-4xl md:text-5xl">
            Discover, bundle, and order —{" "}
            <span className="text-[var(--primary-color)]">in one conversation</span>
          </h1>
          <p className="mt-4 text-lg text-[var(--secondary-color)] sm:text-xl">
            Find products, add to cart, and pay — all through chat. No forms, no friction.
          </p>
        </motion.div>

        {/* Right: stacked capability cards */}
        <div className="flex w-full flex-col gap-4 self-end sm:w-auto sm:min-w-[320px] lg:min-w-[340px]">
          {CAPABILITIES.map((cap, i) => (
            <motion.div
              key={cap.title}
              initial={{ opacity: 0, x: 24, scale: cap.title === "Discover" ? 0.96 : 1 }}
              animate={{
                opacity: 1,
                x: 0,
                scale: 1,
              }}
              transition={{
                duration: cap.title === "Discover" ? 0.6 : 0.4,
                delay: cap.title === "Discover" ? 0.05 : 0.1 + i * 0.1,
                ease: [0.22, 1, 0.36, 1],
              }}
              className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-5 transition-colors hover:border-[var(--primary-color)]/50"
            >
              <span className="text-2xl" role="img" aria-hidden>
                {cap.icon}
              </span>
              <h3 className="mt-3 font-semibold text-[var(--card-foreground)]">
                {cap.title}
              </h3>
              <p className="mt-1 text-sm text-[var(--muted)]">{cap.description}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
