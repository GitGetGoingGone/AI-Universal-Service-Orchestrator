"use client";

import { motion } from "framer-motion";

const PROMPTS = [
  "Find flowers for delivery",
  "Plan a date night",
  "Best birthday gifts under $50",
  "Show me chocolates",
  "I need a limo for tonight",
];

export type ExamplePromptsProps = {
  onSelect: (prompt: string) => void;
};

export function ExamplePrompts({ onSelect }: ExamplePromptsProps) {
  return (
    <section className="px-4 pb-8">
      <div className="mx-auto max-w-4xl">
        <p className="mb-4 text-center text-sm text-[var(--muted)]">
          Try one of these:
        </p>
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="flex flex-wrap justify-center gap-2"
        >
          {PROMPTS.map((prompt) => (
            <button
              key={prompt}
              type="button"
              onClick={() => onSelect(prompt)}
              className="rounded-full border border-[var(--border)] bg-[var(--card)] px-4 py-2 text-sm text-[var(--card-foreground)] transition-colors hover:border-[var(--primary-color)]/50 hover:bg-[var(--primary-color)]/10"
            >
              {prompt}
            </button>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
