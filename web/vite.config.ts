import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  base: "./",
  plugins: [react()],
  build: {
    target: "es2022",
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes("echarts") || id.includes("zrender")) return "echarts";
          if (id.includes("@tanstack")) return "table";
          if (id.includes("node_modules/react-dom") || id.includes("node_modules/react/")) return "react";
        },
      },
    },
  },
  preview: { host: "127.0.0.1", port: 4789, strictPort: true },
  server: { host: "127.0.0.1", port: 4789, strictPort: true },
});
