import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#f7f8fa",
        ink: "#111827",
        muted: "#6b7280",
        line: "#e5e7eb",
        panel: "#ffffff",
        accent: "#2563eb",
      },
      boxShadow: {
        soft: "0 18px 45px -32px rgb(15 23 42 / 0.35)",
      },
    },
  },
  plugins: [],
};

export default config;
