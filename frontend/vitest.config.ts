import path from "node:path";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

/*
 * Run with `npm run test`. Deliberately not part of `npm run build`: the build stays a
 * build, and the reviewer runs the suite as its own command, the same way pytest is not
 * wired into uvicorn.
 *
 * jsdom and not a browser: these tests assert DOM structure, class contracts and focus
 * placement, all of which jsdom carries. Anything that needs real layout or a real
 * disabled-blur belongs in the qa-tester's Playwright pass, not here.
 */
export default defineConfig({
  plugins: [react()],
  resolve: {
    // The same alias tsconfig.json declares. Vitest resolves through Vite, not tsc.
    alias: { "@": path.resolve(__dirname, "src") },
  },
  test: {
    environment: "jsdom",
    include: ["tests/**/*.test.tsx"],
    setupFiles: ["./vitest.setup.ts"],
  },
});
