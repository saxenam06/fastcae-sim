/**
 * Designs: every design a flow made, and its process step by step (LOP-21; the engineer, 10 October
 * 23:47, 11 October 00:01 and 02:08). The shell's three columns: the designs on the left, grouped by
 * the flow that made them, each a card with its numbers marked pass or fail; the chosen design's
 * flow in the centre, a tab a step, each drawn as its kind needs (`Process.tsx`); the step's card on
 * the right. Every flow tried keeps its own tabs. The second page holds every optimisation run.
 *
 * The page before (a comparison table over one 3D view, the organic and CAD buttons, the product's
 * blank frame of rungs and charts) is archived in `archive/web/designs-v2/`.
 */

import type { Tab, TabProps } from "../app/tab";
import { PageHead, Section } from "../panel/page";
import { OptimisationView } from "./Optimisation";
import { ProcessCard, ProcessRail, ProcessStage } from "./Process";

function Stage(props: TabProps) {
  if (props.page === "optimisation") {
    return (
      <div className="stage-scroll cp-scroll">
        <div className="cp-page">
          <PageHead kicker="Optimisation" title="Every run" sub="Where an optimiser puts the material, from the contract's interfaces: a hypothesis for the drawing and FE to judge" />
          <Section title="Topology optimisation" aside="the first loop's prototype (topo.py, topo_free.py): a hypothesis, not a judgement">
            <OptimisationView />
          </Section>
        </div>
      </div>
    );
  }
  return <ProcessStage {...props} />;
}

export const designsTab: Tab = { Rail: ProcessRail, Stage, Card: ProcessCard, cardName: "The step" };
