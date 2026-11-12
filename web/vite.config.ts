import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The build lands inside the Python package, which serves it at "/".
export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: { outDir: "../src/brainfold/panel", emptyOutDir: true },
  server: { proxy: { "/api": "http://127.0.0.1:8020" } },
});
