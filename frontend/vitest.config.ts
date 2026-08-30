import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

/** Configure deterministic browser-like component tests. */
export default defineConfig({
  plugins: [react()],
  test: { environment: "jsdom", setupFiles: ["./src/test/setup.ts"], globals: true },
});
