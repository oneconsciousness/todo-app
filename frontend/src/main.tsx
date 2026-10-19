import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./styles/index.css";

const container = document.getElementById("root");
if (!container) throw new Error("index.html is missing the #root element");

createRoot(container).render(
  <StrictMode>
    <main>
      <h1>To Do</h1>
    </main>
  </StrictMode>,
);
console.info("web app started");
