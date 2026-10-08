/**
 * The Campaigns tab: attempts at a task, step by step. What did a solver try on a contract, why,
 * and what came of it?
 *
 * Four pages over one campaign - its steps, its hypotheses, its trace of tool calls, its budget -
 * with the rail listing campaigns by the contract they attempt, and the card holding the step in
 * focus as its decision record. Nothing has made a campaign yet (the agent is AGT-1 onwards), so
 * every page draws its frame: template rows in words, the plan's stop rules, arms, statuses, seeds
 * and tools, and the few things that are real now - which contracts could start a campaign, and
 * each contract's budget. Every page reads the records through ./records.ts, so the same code
 * draws the rows once campaigns are recorded.
 */

import type { ReactElement } from "react";
import { shortTitle } from "../app/product";
import type { Tab, TabProps } from "../app/tab";
import { BudgetPage } from "./Budget";
import { StepCard } from "./Card";
import { HypothesesPage } from "./Hypotheses";
import { CampaignsRail } from "./Rail";
import { StepsPage } from "./Steps";
import { TracePage } from "./Trace";
import { inView } from "./records";
import { ARM } from "./words";
import "./campaigns.css";

const PAGES: Record<string, (props: TabProps) => ReactElement> = {
  steps: StepsPage,
  hypotheses: HypothesesPage,
  trace: TracePage,
  budget: BudgetPage,
};

function CampaignsStage(props: TabProps) {
  const Page = PAGES[props.page] ?? StepsPage;
  return <Page {...props} />;
}

export const campaignsTab: Tab = {
  Rail: CampaignsRail,
  Stage: CampaignsStage,
  Card: StepCard,
  cardName: "The step",
  context: ({ snap, route }) => {
    const { campaign, contract } = inView(snap, route);
    if (!campaign) return null;
    return {
      name: campaign.id,
      detail: `${contract ? shortTitle(contract.title) : campaign.contract} · ${ARM[campaign.arm].label}`,
    };
  },
};
