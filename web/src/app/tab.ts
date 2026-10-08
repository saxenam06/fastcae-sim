/**
 * What a tab gives the shell: its rail, its stage (the page in view), its card, and what the bar
 * says is in view. The shell draws the frame, the tabs and the page tabs; a tab draws only inside.
 */

import type { ReactElement } from "react";
import type { Snapshot } from "../records/types";
import type { Go, Route } from "./route";

export interface TabProps {
  snap: Snapshot;
  route: Route;
  go: Go;
  /** The page in view: the route's, or the view's first. */
  page: string;
}

export interface CardProps extends TabProps {
  onCollapse: () => void;
}

export interface Tab {
  Rail: (props: TabProps) => ReactElement;
  /** Drawn inside `.stage-body`, which is positioned: fill it with `.stage-scroll` to scroll. */
  Stage: (props: TabProps) => ReactElement;
  Card: (props: CardProps) => ReactElement;
  /** What the card says on its strip when folded away. */
  cardName: string;
  /** What the bar's third lockup names: the record in view, or null for the factory. */
  context?: (props: TabProps) => { name: string; detail: string } | null;
}
