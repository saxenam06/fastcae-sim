/**
 * The Contracts tab: the tasks - what a design must meet, every value with where it came from.
 *
 * The one tab with real data today, so it is the one that shows a contract whole: the rail lists
 * the contracts by stage, the stage shows one of five readings of the contract in view (what binds a
 * design, the full sheet, the validator's check, the sources, the file), and the card shows the
 * entry in focus, an assumption, or the contract itself. Each page is a file of its own in this
 * folder; this one only puts them in the shell's frame.
 */

import "./contracts.css";
import { shortTitle } from "../app/product";
import type { Tab, TabProps } from "../app/tab";
import { Blank } from "../panel/bits";
import { Binding } from "./Binding";
import { Card } from "./Card";
import { Check } from "./Check";
import { Json } from "./Json";
import { contractIn, verdictOf } from "./model";
import { Rail } from "./Rail";
import { Sheet } from "./Sheet";
import { Sources } from "./Sources";

function Stage({ snap, route, go, page }: TabProps) {
  const c = contractIn(snap, route.id);
  if (!c) {
    return (
      <div className="stage-scroll ct-page">
        <Blank title="No contract yet" waits="a contract is posed from a published requirement" />
      </div>
    );
  }
  const props = { snap, c, focus: route.focus, go };
  switch (page) {
    case "sheet":
      return <Sheet {...props} />;
    case "check":
      return <Check {...props} />;
    case "sources":
      return <Sources {...props} />;
    case "json":
      // Keyed by the contract so a "copied" note never carries over to another contract's file.
      return <Json key={c.id} {...props} />;
    default:
      return <Binding {...props} />;
  }
}

export const contractsTab: Tab = {
  Rail,
  Stage,
  Card,
  cardName: "The entry",
  context: ({ snap, route }) => {
    const c = contractIn(snap, route.id);
    if (!c) return null;
    if (!c.loaded) return { name: c.id, detail: "does not load" };
    return { name: shortTitle(c.title), detail: `${c.stage} · ${verdictOf(c).words}` };
  },
};
