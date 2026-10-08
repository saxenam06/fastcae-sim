/**
 * The shell: fastcae's frame, zenryx's tabs.
 *
 * From fastcae-v1:ui/src/app/App.tsx, the frame only: the bar with the mark and three lockups, the
 * main tabs, the rail and the card on either side of the stage, each resizable and remembered, the
 * card folding to a strip, and the title block. Everything inside belongs to the tab in view
 * (./tab.ts). The project upload, the canvases and the agent bar are not carried over.
 *
 * Nothing on screen comes from anything but the snapshot (../records/source.ts).
 */

import { useEffect, useState } from "react";
import { campaignsTab } from "../campaigns/Campaigns";
import { contractsTab } from "../contracts/Contracts";
import { dataTab } from "../data/Data";
import { datapoints as countDatapoints } from "../data/kinds";
import { designsTab } from "../designs/Designs";
import { flowTab } from "../flow/Flow";
import { Splitter } from "../panel/Splitter";
import { Hash } from "../panel/bits";
import { loadSnapshot } from "../records/source";
import type { Snapshot } from "../records/types";
import type { View } from "./product";
import { ART, PRODUCT, VENDOR, VIEWS, viewSpec } from "./product";
import { useRoute } from "./route";
import type { Tab, TabProps } from "./tab";

const TABS: Record<View, Tab> = {
  flow: flowTab,
  contracts: contractsTab,
  campaigns: campaignsTab,
  designs: designsTab,
  data: dataTab,
};

export function App() {
  const [snap, setSnap] = useState<Snapshot | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [route, go] = useRoute();

  // Pane widths, remembered between sessions, as fastcae's are.
  const [railWidth, setRailWidth] = useState(() => remembered("zenryx.rail", 300));
  const [cardWidth, setCardWidth] = useState(() => remembered("zenryx.card", 380));
  const [cardOpen, setCardOpen] = useState(true);

  useEffect(() => {
    loadSnapshot().then(setSnap, (caught) => setError(String(caught)));
  }, []);

  useEffect(() => {
    try {
      localStorage.setItem("zenryx.rail", String(railWidth));
      localStorage.setItem("zenryx.card", String(cardWidth));
    } catch {
      // Private windows and blocked site data. A forgotten width is not worth an error.
    }
  }, [railWidth, cardWidth]);

  const spec = viewSpec(route.view);
  const tab = TABS[route.view];
  const page = spec.pages.some((p) => p.id === route.page) ? (route.page as string) : spec.pages[0].id;
  const props: TabProps | null = snap ? { snap, route, go, page } : null;
  const context = props ? (tab.context?.(props) ?? factory(props.snap)) : null;

  return (
    <div
      className="shell"
      data-open={snap !== null}
      style={
        snap
          ? { gridTemplateColumns: `${railWidth}px minmax(0, 1fr) ${cardOpen ? cardWidth : 28}px` }
          : undefined
      }
    >
      <header className="topbar">
        <img className="mark" src={ART.mark} alt="" aria-hidden="true" />
        <span className="lockup">
          <b>{VENDOR.name}</b>
          <em>{VENDOR.tagline}</em>
        </span>
        <span className="divider" />
        <span className="lockup">
          <b>{PRODUCT.name}</b>
          <em>{PRODUCT.tagline}</em>
        </span>
        {context ? (
          <>
            <span className="divider" />
            <span className="lockup">
              <b>{context.name}</b>
              <em>{context.detail}</em>
            </span>
          </>
        ) : null}
        <nav className="stages main-tabs">
          {VIEWS.map((v) => (
            <button
              key={v.id}
              data-active={route.view === v.id}
              data-ready={v.ready}
              onClick={() => go({ view: v.id })}
              title={v.ready ? v.summary : `${v.summary} - not built yet`}
            >
              {v.label}
            </button>
          ))}
        </nav>
        <span className="spacer" />
      </header>

      {props ? (
        <>
          <div className="rail">
            <div className="rail-scroll">
              <tab.Rail {...props} />
            </div>
            <Splitter side="right" onResize={(d) => setRailWidth((w) => clampPane(w + d))} />
          </div>

          <div className="stage">
            <nav className="stage-tabs">
              {spec.pages.map((p) => (
                <button
                  key={p.id}
                  data-active={page === p.id}
                  onClick={() => go({ page: p.id, focus: null })}
                  title={p.summary}
                >
                  {p.label}
                </button>
              ))}
              <span className="stage-tabs-spacer" />
            </nav>
            <div className="stage-body">
              <tab.Stage {...props} />
            </div>
          </div>

          <div className="card-pane">
            {cardOpen ? (
              <>
                <Splitter side="left" onResize={(d) => setCardWidth((w) => clampPane(w - d))} />
                <tab.Card {...props} onCollapse={() => setCardOpen(false)} />
              </>
            ) : (
              <button className="pane-strip" onClick={() => setCardOpen(true)} title="Open it again">
                <span>{tab.cardName}</span>
              </button>
            )}
          </div>

          <TitleBlock snap={props.snap} />
        </>
      ) : (
        <div className="loading">{error ? <div className="error">{error}</div> : "reading the snapshot…"}</div>
      )}
    </div>
  );
}

/** The drawing's title block: what this is a picture of, and on what evidence. Always visible. */
function TitleBlock({ snap }: { snap: Snapshot }) {
  const r = snap.records;
  const frozen = snap.contracts.filter((c) => c.stage === "frozen").length;
  // Counted as the Data tab counts them, kind by kind (A-E), so the two can never disagree.
  const datapoints = countDatapoints(snap);
  return (
    <footer className="titleblock">
      <span>
        snapshot <Hash value={snap.hash} />
      </span>
      <span>zenryx {snap.zenryx}</span>
      <span>contract schema {snap.contract_schema}</span>
      <span>{snap.rules.length} validator rules</span>
      <span>
        {snap.contracts.length} contracts · {frozen} frozen
      </span>
      <span>
        {r.campaigns.length} campaigns · {r.candidates.length} designs · {r.evaluations.length} evaluations
      </span>
      <span>{datapoints} datapoints</span>
      <span style={{ marginLeft: "auto" }}>bundled snapshot · no server</span>
    </footer>
  );
}

function factory(snap: Snapshot): { name: string; detail: string } {
  const frozen = snap.contracts.filter((c) => c.stage === "frozen").length;
  return { name: "the factory", detail: `${snap.contracts.length} contracts · ${frozen} frozen` };
}

const MIN_PANE = 220;
const MAX_PANE = 900;

function clampPane(width: number): number {
  return Math.min(Math.max(width, MIN_PANE), MAX_PANE);
}

function remembered(key: string, fallback: number): number {
  try {
    const stored = Number(localStorage.getItem(key));
    return Number.isFinite(stored) && stored > 0 ? clampPane(stored) : fallback;
  } catch {
    return fallback;
  }
}
