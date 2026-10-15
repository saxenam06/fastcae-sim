// The shared sheets come first: a tab's own sheet, imported by its module through App, then
// lands after them and refines them at equal specificity.
import "./styles/tokens.css";
import "./styles/shell.css";
import "./styles/rail.css";
import "./styles/campaign.css";
import "./styles/zenryx.css";
import "./styles/page.css";
import "./styles/volumes.css";
import "./styles/section.css";
import "./styles/process.css";
import "./styles/agent.css";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./app/App";
import { Crash } from "./app/Crash";
import { SectionProvider } from "./render/Section";

// One cut section for every 3D view, as in fastcae: the plane is in the views' shared frame.
createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Crash>
      <SectionProvider>
        <App />
      </SectionProvider>
    </Crash>
  </StrictMode>,
);
