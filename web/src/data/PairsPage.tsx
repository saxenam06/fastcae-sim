/**
 * Pairs: the counterfactual pairs the record holds, and any two contracts compared entry by entry.
 *
 * A counterfactual pair is two contracts one requirement apart, and none has been written yet, so
 * the pairs table is drawn empty with the shape a pair will take. The comparison underneath is real
 * today: it measures how far apart two of the contracts that exist are, which is what a generated
 * pair will have to beat - one requirement, not dozens of entries.
 */

import { Fragment, useMemo, useState } from "react";
import { LAYERS, shortTitle } from "../app/product";
import type { TabProps } from "../app/tab";
import { Blank, Block, Prov } from "../panel/bits";
import type { EntryView, Provenance } from "../records/types";
import { compareContracts, countBy, DIFFERENCE, type Compared, type Difference } from "./compare";

type Show = "differ" | Difference;

const SHOWS: { id: Show; label: string }[] = [
  { id: "differ", label: "all that differ" },
  { id: "different", label: "different" },
  { id: "only_a", label: "only in A" },
  { id: "only_b", label: "only in B" },
  { id: "same", label: "the same" },
];

export function PairsPage({ snap, go }: TabProps) {
  const contracts = snap.contracts;
  const pairs = snap.records.pairs;
  const name = (id: string) => {
    const c = contracts.find((x) => x.id === id);
    return c ? shortTitle(c.title) : id;
  };
  const [aId, setA] = useState(contracts[0]?.id ?? "");
  const [bId, setB] = useState(contracts[1]?.id ?? contracts[0]?.id ?? "");
  const [show, setShow] = useState<Show>("differ");
  const a = contracts.find((c) => c.id === aId);
  const b = contracts.find((c) => c.id === bId);
  const rows = useMemo(() => (a && b ? compareContracts(a, b) : []), [a, b]);
  const n = countBy(rows);
  const differ = n.different + n.only_a + n.only_b;
  const shown = rows.filter((r) => (show === "differ" ? r.how !== "same" : r.how === show));
  const count = (s: Show) => (s === "differ" ? differ : n[s]);

  return (
    <>
      <Block title="Counterfactual pairs" count={pairs.length} aside="two contracts, one requirement apart">
        <div className="tbl-wrap">
          <table className="tbl data-table">
            <thead>
              <tr>
                <th>Contract A</th>
                <th>Contract B</th>
                <th>The requirement changed</th>
                <th>How the design changed</th>
              </tr>
            </thead>
            <tbody>
              {pairs.length ? (
                pairs.map((p) => (
                  <tr key={p.id}>
                    <td>{name(p.a)}</td>
                    <td>{name(p.b)}</td>
                    <td className="mono">{p.changed}</td>
                    <td>{p.effect}</td>
                  </tr>
                ))
              ) : (
                <tr className="template">
                  <td>a frozen contract</td>
                  <td>the same contract, one requirement changed</td>
                  <td>the entry changed, A's value and B's</td>
                  <td>what changed in the best designs, by the judge</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        {pairs.length ? null : (
          <div className="data-gap">
            <Blank
              title="No counterfactual pairs yet"
              waits="Not built yet: counterfactual contracts are written by the generator and recorded (DAT-1)"
            />
          </div>
        )}
      </Block>

      <Block title="Compare two contracts" aside="entry by entry, by path">
        <div className="data-compare-pick">
          <Side side="A" id={aId} onPick={setA} snap={snap} go={go} />
          <Side side="B" id={bId} onPick={setB} snap={snap} go={go} />
        </div>

        <p className="data-verdict">
          A counterfactual pair differs in one requirement.{" "}
          {aId === bId ? (
            "These are the same contract: pick two."
          ) : (
            <>
              These two differ in <b className="num">{differ}</b> {differ === 1 ? "entry" : "entries"}.
            </>
          )}
        </p>

        <div className="data-filter">
          <div className="segmented">
            {SHOWS.map((s) => (
              <button
                key={s.id}
                data-active={show === s.id}
                onClick={() => setShow(s.id)}
                title={s.id === "differ" ? "different, only in A, only in B" : DIFFERENCE[s.id]}
              >
                {s.label} <span className="num">{count(s.id)}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="tbl-wrap">
          <table className="tbl data-table data-compare">
            <thead>
              <tr>
                <th>Entry</th>
                <th>A's value</th>
                <th>B's value</th>
                <th>A's provenance</th>
                <th>B's provenance</th>
              </tr>
            </thead>
            <tbody>
              {LAYERS.map((layer) => {
                const these = shown.filter((r) => r.layer === layer.id);
                if (!these.length) return null;
                return (
                  <Fragment key={layer.id}>
                    <tr className="data-layer-row">
                      <th colSpan={5} title={layer.words}>
                        {layer.label} <span className="count">{these.length}</span>
                      </th>
                    </tr>
                    {these.map((r) => (
                      <Row key={r.path} row={r} />
                    ))}
                  </Fragment>
                );
              })}
              {shown.length ? null : (
                <tr className="template">
                  <td colSpan={5}>no entries of this kind between these two</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Block>
    </>
  );
}

function Side({
  side,
  id,
  onPick,
  snap,
  go,
}: {
  side: "A" | "B";
  id: string;
  onPick: (id: string) => void;
  snap: TabProps["snap"];
  go: TabProps["go"];
}) {
  return (
    <span className="data-compare-side">
      <label>
        <span className="data-key">{side}</span>
        <select value={id} onChange={(e) => onPick(e.target.value)}>
          {snap.contracts.map((c) => (
            <option key={c.id} value={c.id}>
              {shortTitle(c.title)}
            </option>
          ))}
        </select>
      </label>
      <button className="link" onClick={() => go({ view: "contracts", id })} title={`Open ${id}`}>
        open
      </button>
    </span>
  );
}

function Row({ row }: { row: Compared }) {
  return (
    <tr data-how={row.how} title={DIFFERENCE[row.how]}>
      <td className="data-entry">
        <span>{row.label}</span>
        <span className="data-path mono">{row.path}</span>
      </td>
      <td className="mono data-value">{row.a ? row.a.value : <span className="dim">-</span>}</td>
      <td className="mono data-value">{row.b ? row.b.value : <span className="dim">-</span>}</td>
      <td>
        <Source entry={row.a} />
      </td>
      <td>
        <Source entry={row.b} />
      </td>
    </tr>
  );
}

function Source({ entry }: { entry: EntryView | null }) {
  if (!entry) return <span className="dim">-</span>;
  const words = sourceOf(entry.provenance);
  return (
    <span className="data-source">
      <Prov kind={entry.provenance.kind} />
      {words ? (
        <span className="data-source-words" title={words}>
          {words}
        </span>
      ) : null}
    </span>
  );
}

/** Where a value came from, in the fewest words that identify it. */
function sourceOf(p: Provenance): string {
  if (p.citation) return p.citation;
  if (p.tool) return [p.tool, p.tool_version].filter(Boolean).join(" ");
  if (p.assumption_id) return p.assumption_id;
  if (p.who) return [p.who, p.when].filter(Boolean).join(", ");
  return "";
}
