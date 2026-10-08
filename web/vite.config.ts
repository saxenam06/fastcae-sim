import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  // Relative asset paths, so the built page opens from any folder or static host as well as here.
  base: "./",
  server: {
    // zenryx's own ports: fastcae's UI is on 5183 and its API on 8021 (CLAUDE.md).
    port: 5190,
    strictPort: true,
    // The API (PLT-5) will be a separate process on 8030; proxied so the browser stays on one origin.
    proxy: { "/api": { target: "http://127.0.0.1:8030", changeOrigin: true } },
  },
});
