# Mechanical AI, Inc. (MEKINT): company research

Researched 2026-10-04.

## Company (verified)

- **Name / product:** Mechanical AI, Inc. Product: **MEKINT** ("mechanical intelligence"), an AI agent that
  autonomously executes iterative mechanical design workflows from user-defined goals and constraints.
- **Founded:** 2024.
- **Location:** 5831 Forward Ave #251, Pittsburgh, PA 15217.
- **Contact:** contact@mechanicalai.com
- **Backers listed on the site:** TQ Ventures (tq.vc), CarbonBlack (carbonblackgroup.com), Plug and Play Tech Center.
- **Funding:** seed round, April 2026 (stated in the job posting).
- **Size:** about 3 employees (PitchBook, seen via a search snippet only; the PitchBook page returned 403). *Unverified.*
- **Product site** mekint.com refused connections when fetched on 2026-10-04.

## Founder and CEO (verified)

- **Jinwook Lee, Ph.D.** in Aerospace Engineering, MIT.
- Ex-SpaceX: "designed critical turbomachinery components for the fully reusable, next-generation rocket engine, Raptor."
- CarbonBlack describes its role as a "co-founding experience", including business-development collaboration.
- Stated technical focus: mechanical design, topological optimization, physical-complexity automation.

## Open roles (verified, careers page)

All four use the same online form: **name, phone, email, résumé attachment. There is no cover-letter field.**
No take-home or hiring process is described. Remote or onsite is not stated.

1. **Research Engineer, Mechanical Intelligence** (target role)
   - Agentic data-generation pipelines for manufacturing-grade synthetic designs with embedding-friendly representations.
   - Modular tool interfaces and execution protocols: structural, fluid, heat-transfer, aerothermodynamic analysis, plus automated CAD.
   - Build and train mechanical design agents.
   - Must-have: first-principles thinking across thermal, fluid, structural and dynamic systems; *demonstrable* governing-parameter
     identification and reduced-order models; speed; Python.
   - Nice-to-have: Claude Code multi-agent workflows; numerical analysis / design optimization; AI frameworks;
     CAD (CATIA, NX, FreeCAD); cloud batch processing (GCP/AWS).
2. **Machine Learning Research Engineer, Mechanical Intelligence**
   - Core model architecture for design agents; representation learning; training pipelines with curriculum and evaluation
     metrics; subagent behaviour and tool-use reliability.
   - Must-have: math foundations; transformer / vision / multimodal training; PyTorch or TensorFlow.
3. **CAD Engineer, Mechanical Intelligence**
   - Characterize designs (key parameters and constraints); build **CAD templates for synthetic designs**.
   - Must-have: **Siemens NX**. Nice-to-have: tooling design (injection molding, die casting, stamping), Ansys / Abaqus.
4. **Full-Stack Software Engineer, Mechanical Intelligence**
   - Production platform powered by AI agents; React/Electron; Python or Node backend; GCP/AWS.
   - Must-have: "Exceptional proficiency in AI-native development workflows using Claude Code".
   - Nice-to-have: Three.js, WebGL, OpenCascade.js.

## What the roles imply about MEKINT's architecture (inference)

- An LLM orchestrator with subagents that call CAD (NX) and CAE tools.
- A synthetic-design data engine: CAD templates, then parameter sampling, then physics labels, then training data.
- Their own models trained on that data, plus an Electron desktop app.

## Sources

- https://mechanicalai.com/careers (verified)
- https://mechanicalai.com/about (verified)
- https://mechanicalai.com (verified)
- https://www.carbonblackgroup.com/mechanicalai (verified: CEO background)
- https://pitchbook.com/profiles/company/686729-98 (403; snippet only)
- https://beamstart.com/@mechanical-ai-inc-17388109652708 (403; snippet only)
