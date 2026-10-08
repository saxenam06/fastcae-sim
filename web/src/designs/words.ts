/**
 * The words the Designs tab draws: the stages a design passes through, from the machined core to
 * its modes, and the label ladder every design is placed on (plan §7.2).
 *
 * Each stage names the feature that will build it, so a column with nothing in it still says what
 * fills it. The rungs are the plan's, word for word in the hover: a design is always labelled with
 * the rung it has reached and never called "production-ready". Kept here while the tabs are built
 * side by side; they belong beside the other words in app/product.ts.
 */

import type { Rung } from "../records/types";

export type DesignStage = "core" | "structure" | "join" | "castability" | "mesh" | "statics" | "modes";

/** A design's stages in the order they run, each with the method it runs and what builds it. */
export const STAGES: {
  id: DesignStage;
  label: string;
  method?: string;
  /** What the template row says the cell will hold. */
  template: string;
  /** The feature or PBI that builds the stage. */
  builds: string;
  words: string;
}[] = [
  {
    id: "core",
    label: "Core",
    method: "CadQuery",
    template: "seats, faces and flanges, machined",
    builds: "GEO-1",
    words: "The machined core, built from the contract's interfaces",
  },
  {
    id: "structure",
    label: "Structure",
    method: "field",
    template: "grown in the design domain",
    builds: "GEO, OPT",
    words: "The load-bearing structure, from the hypothesis's formulation in field space",
  },
  {
    id: "join",
    label: "Join",
    template: "one watertight solid",
    builds: "GEO",
    words: "The core and the structure fused into one watertight solid",
  },
  {
    id: "castability",
    label: "Castability",
    template: "draft, pull, undercuts, least wall",
    builds: "PRC",
    words: "The process profile's rules, checked on the built part",
  },
  {
    id: "mesh",
    label: "Mesh",
    template: "TET10, checked against the solid",
    builds: "PHY",
    words: "The TET10 mesh, checked against the solid's volume before any solve",
  },
  {
    id: "statics",
    label: "Statics",
    template: "misalignment, tilt, ovalisation, per case",
    builds: "PHY-1",
    words: "Every static load case, solved on cuDSS",
  },
  {
    id: "modes",
    label: "Modes",
    template: "modes against the gear orders",
    builds: "PHY",
    words: "Mounted and free-free modes, against the gear orders at the check speeds",
  },
];

/** The label ladder (plan §7.2). `own` marks the rungs the platform reaches without a partner. */
export const RUNG: Record<Rung, { label: string; needs: string; signs: string; own: boolean }> = {
  none: {
    label: "no rung yet",
    needs: "Not yet simulation-feasible",
    signs: "-",
    own: true,
  },
  simulation_feasible: {
    label: "simulation-feasible",
    needs: "The contract's verdict met on the TET10 proof, with margins",
    signs: "The deterministic evaluator",
    own: true,
  },
  process_rule_feasible: {
    label: "process-rule-feasible",
    needs: "Every rule of the process profile passed on the built geometry",
    signs: "The deterministic checker",
    own: true,
  },
  process_simulated: {
    label: "process-simulated",
    needs: "Distortion, residual stress and supports simulated for the chosen orientation",
    signs: "A process simulation (later)",
    own: false,
  },
  prototype_validated: {
    label: "prototype-validated",
    needs: "Built, machined, measured against the prediction",
    signs: "A test with a partner",
    own: false,
  },
  production_qualified: {
    label: "production-qualified",
    needs: "A qualified process, production controls, NDE, acceptance (PPAP)",
    signs: "The customer's quality system",
    own: false,
  },
};

/** The ladder from the bottom rung up; `none` is not a rung. */
export const RUNG_ORDER: Rung[] = [
  "simulation_feasible",
  "process_rule_feasible",
  "process_simulated",
  "prototype_validated",
  "production_qualified",
];
