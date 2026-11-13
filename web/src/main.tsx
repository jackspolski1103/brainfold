import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import "./index.css";

// Dark unless the person chose light; the choice lives in this browser only.
let stored: string | null = null;
try {
  stored = localStorage.getItem("theme");
} catch {
  // Storage can be blocked; the panel then stays dark.
}
document.documentElement.classList.toggle("light", stored === "light");

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
