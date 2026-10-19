import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { NavigationProvider } from "../src/components/ui/link.tsx";
import "../src/styles/index.css";
import { Gallery } from "./gallery.tsx";

const container = document.getElementById("root");
if (!container) throw new Error("design/index.html is missing the #root element");

// Links in the gallery stay on the page; the app's router takes this role later.
const stayOnPage = (): void => undefined;

createRoot(container).render(
  <StrictMode>
    <NavigationProvider navigate={stayOnPage}>
      <Gallery />
    </NavigationProvider>
  </StrictMode>,
);
