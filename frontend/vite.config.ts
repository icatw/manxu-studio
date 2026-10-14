import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import tsconfigPaths from "vite-tsconfig-paths";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react(), tailwindcss(), tsconfigPaths()],
  server: { proxy: { "/api": process.env.VITE_API_PROXY_TARGET ?? "http://localhost:8000" } },
  test: { environment: "jsdom", setupFiles: ["./src/test/setup.ts"] },
});
