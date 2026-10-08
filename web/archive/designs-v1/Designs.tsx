/**
 * The Designs tab: every design a campaign made - how it was built, how it was tested, its grade
 * and its rung.
 *
 * Three pages over all designs - the grid (a design a row, a stage a column, as fastcae's campaign
 * grid), the trade-off of mass against the worst margin, and every evaluation by scenario - with the
 * rail listing designs by campaign and the card holding the design in view. Nothing has made a
 * design yet (geometry is GEO-1, the judge PHY-1 onwards), so the pages draw their frames: template
 * rows in words, the stages and the rung ladder, and what is real now - the verdict each contract
 * sets and the scenarios each will be tested under. The same code draws the rows once designs are
 * recorded.
 */

import type { ReactElement } from "react";
import type { Tab, TabProps } from "../app/tab";
import { candidateById } from "../campaigns/records";
import { DesignCard } from "./Card";
import { EvaluationsPage } from "./Evaluations";
import { GridPage } from "./Grid";
import { DesignsRail } from "./Rail";
import { TradeOffPage } from "./TradeOff";
import { RUNG } from "./words";
import "./designs.css";

const PAGES: Record<string, (props: TabProps) => ReactElement> = {
  grid: GridPage,
  tradeoff: TradeOffPage,
  evaluations: EvaluationsPage,
};

function DesignsStage(props: TabProps) {
  const Page = PAGES[props.page] ?? GridPage;
  return <Page {...props} />;
}

export const designsTab: Tab = {
  Rail: DesignsRail,
  Stage: DesignsStage,
  Card: DesignCard,
  cardName: "The design",
  context: ({ snap, route }) => {
    const design = candidateById(snap, route.id);
    if (!design) return null;
    return { name: design.id, detail: `${RUNG[design.rung].label} · ${design.campaign}` };
  },
};
