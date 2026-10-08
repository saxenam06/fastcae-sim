/**
 * Data: what the record becomes, and what it can train.
 *
 * The rail lists the datapoint kinds, the cuts made from campaigns and the task types; the card is
 * the one in focus; the stage holds four pages - the axes every datapoint sits on, the kinds, the
 * twenty task types with their graders, and the pairs. What exists is shown from the snapshot (the
 * contracts, the scenarios they imply, the graders that exist, any two contracts compared); what
 * the agent, the judge and the record will make is drawn as structure and left blank.
 */

import type { ReactElement } from "react";
import type { Tab, TabProps } from "../app/tab";
import { AxesPage } from "./AxesPage";
import { DataCard } from "./DataCard";
import { DataRail } from "./DataRail";
import { DatapointsPage } from "./DatapointsPage";
import { PairsPage } from "./PairsPage";
import { TasksPage } from "./TasksPage";
import "./data.css";

const PAGES: Record<string, (props: TabProps) => ReactElement> = {
  axes: AxesPage,
  datapoints: DatapointsPage,
  tasks: TasksPage,
  pairs: PairsPage,
};

function DataStage(props: TabProps) {
  const Page = PAGES[props.page] ?? AxesPage;
  return (
    <div className="stage-scroll data-page">
      <Page {...props} />
    </div>
  );
}

export const dataTab: Tab = {
  Rail: DataRail,
  Stage: DataStage,
  Card: DataCard,
  cardName: "The kind",
};
