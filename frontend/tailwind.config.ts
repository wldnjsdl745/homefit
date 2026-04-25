import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#111111",
        paper: "#fffffb",
        cream: "#f7f7f3",
        sand: "#eeeeea",
        coral: "#111111",
        mint: "#111111",
        mustard: "#111111",
        muted: "#6b7280",
        line: "#111111",
        surface: "#fffffb",
        brand: "#111111",
      },
      boxShadow: {
        editorial: "12px 12px 0 #111111",
        soft: "0 16px 40px rgba(17, 17, 17, 0.08)",
      },
    },
  },
  plugins: [],
} satisfies Config;
