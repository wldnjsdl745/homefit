import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "jsdom",
    env: {
      VITE_USE_MOCK_CHAT: "true",
    },
    globals: true,
    setupFiles: "./src/test/setup.ts",
  },
});
