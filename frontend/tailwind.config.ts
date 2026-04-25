import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // 도트/픽셀 팔레트 (게임보이/패미콤 풍)
        ink: "#1a1d2e",
        paper: "#ffffff",
        cream: "#f4ecd0",
        sand: "#e8dab2",
        coral: "#e94560",
        mint: "#4caf50",
        mustard: "#f9a826",
        muted: "#6b7280",
        line: "#1a1d2e",
        surface: "#f4ecd0",
        brand: "#e94560",
      },
      fontFamily: {
        pixel: [
          "DotGothic16",
          '"Press Start 2P"',
          "Galmuri11",
          '"Neo둥근모"',
          "monospace",
        ],
      },
      boxShadow: {
        // 하드 픽셀 그림자 (offset only, no blur)
        pixel: "4px 4px 0 #1a1d2e",
        "pixel-sm": "2px 2px 0 #1a1d2e",
        "pixel-lg": "6px 6px 0 #1a1d2e",
        "pixel-coral": "4px 4px 0 #e94560",
        "pixel-mint": "4px 4px 0 #4caf50",
        soft: "4px 4px 0 #1a1d2e",
      },
    },
  },
  plugins: [],
} satisfies Config;
