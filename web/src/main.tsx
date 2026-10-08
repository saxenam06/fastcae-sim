// The shared sheets come first: a tab's own sheet, imported by its module through App, then
// lands after them and refines them at equal specificity.
import "./styles/tokens.css";
import "./styles/shell.css";
import "./styles/rail.css";
import "./styles/campaign.css";
import "./styles/zenryx.css";
import "./styles/page.css";
import "./styles/volumes.css";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./app/App";
import { Crash } from "./app/Crash";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Crash>
      <App />
    </Crash>
  </StrictMode>,
);
