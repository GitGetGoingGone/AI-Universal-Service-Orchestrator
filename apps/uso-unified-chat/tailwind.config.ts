import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["system-ui", "sans-serif"],
        mono: ["monospace"],
      },
      colors: {
        primary: {
          DEFAULT: "var(--primary-color, #0ea5e9)",
          foreground: "var(--primary-foreground, #fff)",
        },
        secondary: {
          DEFAULT: "var(--secondary-color, #64748b)",
          foreground: "var(--secondary-foreground, #fff)",
        },
      },
    },
  },
  plugins: [],
};

export default config;
