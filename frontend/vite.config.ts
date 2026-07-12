import path from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    proxy: {
      "/upload": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/ask": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/knowledge-graph": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/documents": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
