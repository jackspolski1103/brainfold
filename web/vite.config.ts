import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The build lands inside the Python package, which serves it at "/".
export default defineConfig({
  plugins: [react(), tailwindcss()],
  // Nothing is inlined as a data: address, which the panel's content policy refuses.
  build: { outDir: "../src/brainfold/panel", emptyOutDir: true, assetsInlineLimit: 0 },
  server: { proxy: { "/api": "http://127.0.0.1:8020" } },
});
