import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Proxy /api to the FastAPI backend so the frontend can use same-origin
// relative paths in dev. Backend runs on :8000 by default; override with
// VITE_PROXY_TARGET (e.g. another port) without editing this file.
const target = process.env.VITE_PROXY_TARGET || "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": target,
    },
  },
});
