import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import "./index.css";

const system = matchMedia("(prefers-color-scheme: dark)");
const followSystem = () => document.documentElement.classList.toggle("dark", system.matches);
followSystem();
system.addEventListener("change", followSystem);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
