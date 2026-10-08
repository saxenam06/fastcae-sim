/**
 * The Designs tab's own marks: a stage's name with its method set small beneath it, as fastcae's
 * grid heads read ("Core (CadQuery)"), the rung pill every design carries, and the head each
 * Designs page opens with.
 *
 * The rung pill is solid for the rungs the platform reaches on its own and dashed for the ones that
 * need a partner, so the line says who stands behind the label as well as its words.
 */

import { Count } from "../panel/bits";
import type { Rung, Snapshot } from "../records/types";
import { RUNG } from "./words";

export function StageName({ label, method }: { label: string; method?: string }) {
  return (
    <>
      {label}
      {method ? <span className="dsg-hint">({method})</span> : null}
    </>
  );
}

export function RungPill({ rung }: { rung: Rung }) {
  const r = RUNG[rung];
  return (
    <span
      className="pill dsg-rung"
      data-rung={rung}
      data-own={r.own}
      title={rung === "none" ? r.needs : `${r.needs}\nSigned by: ${r.signs}`}
    >
      {r.label}
    </span>
  );
}

/** The head of every Designs page: how many designs, from how many campaigns, how many pass. */
export function DesignsHead({ snap }: { snap: Snapshot }) {
  const designs = snap.records.candidates;
  const campaigns = new Set(designs.map((d) => d.campaign)).size;
  const passing = designs.filter((d) => d.passed === true).length;
  if (!designs.length)
    return (
      <header className="page-head">
        <h1>No design yet</h1>
        <span className="dim">
          {snap.records.campaigns.length ? "no campaign has made one" : "no campaign has run"} · a design is graded
          against its contract's verdict
        </span>
      </header>
    );
  return (
    <header className="page-head">
      <h1>Every design</h1>
      <span className="dim">
        <Count n={designs.length} /> designs · <Count n={passing} /> pass · <Count n={campaigns} /> campaigns
      </span>
    </header>
  );
}
