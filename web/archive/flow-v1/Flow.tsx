/**
 * Flow: the factory at a glance - where each contract is on its way to data.
 *
 * The rail is the factory's line of stages, the card is the stage in focus, and the stage holds two
 * pages: the contracts through the factory (a contract a row, a stage a column) and one campaign
 * cut into data. Every stage is shown whether or not it is built; one not built says so and names
 * what will make it, because a factory that hides its unbuilt stages cannot show where it leads.
 */

import type { Tab, TabProps } from "../app/tab";
import { CampaignPage } from "./CampaignPage";
import { ContractsPage } from "./ContractsPage";
import { FactoryRail } from "./FactoryRail";
import { FlowCard } from "./FlowCard";
import "./flow.css";

function FlowStage(props: TabProps) {
  return (
    <div className="stage-scroll flow-page">
      {props.page === "campaign" ? <CampaignPage {...props} /> : <ContractsPage {...props} />}
    </div>
  );
}

export const flowTab: Tab = {
  Rail: FactoryRail,
  Stage: FlowStage,
  Card: FlowCard,
  cardName: "The step",
};
