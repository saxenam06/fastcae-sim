/**
 * Datapoints: the kinds A-E (data design §4) and the three cuts made from a campaign (§5), each with
 * what it is, what it trains, how many exist and what makes them; then the families the contracts
 * fall into, because a split is drawn by contract or family and never by scenario.
 *
 * Only kind A has a maker today, and it counts frozen contracts: none yet, so the line under the
 * table says how far the contracts are from becoming tasks.
 */

import { shortTitle } from "../app/product";
import type { TabProps } from "../app/tab";
import { Block, Count, StageDots } from "../panel/bits";
import { CUTS, datapoints, KINDS } from "./kinds";
import { MakingPill } from "./views";

export function DatapointsPage({ snap, route, go }: TabProps) {
  const focus = route.focus;
  const frozen = snap.contracts.filter((c) => c.stage === "frozen").length;
  const families = familiesOf(snap.contracts);
  return (
    <>
      <Block title="The kinds" count={KINDS.length} aside={`${datapoints(snap)} datapoints now`}>
        <div className="tbl-wrap">
          <table className="tbl data-table data-kinds">
            <thead>
              <tr>
                <th>Kind</th>
                <th>What it is</th>
                <th>Trains</th>
                <th className="data-right">Now</th>
                <th>Made by</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {KINDS.map((k) => (
                <tr
                  key={k.letter}
                  data-click="true"
                  data-focus={focus === `kind:${k.letter}`}
                  onClick={() => go({ focus: `kind:${k.letter}` })}
                >
                  <td className="data-name">
                    <span className="data-key">{k.letter}</span> {k.name}
                  </td>
                  <td>{k.what}</td>
                  <td>
                    {k.trains}
                    <span className="data-sub">{k.learning}</span>
                  </td>
                  <td className="num">
                    <Count n={k.count(snap)} />
                  </td>
                  <td>{k.madeBy}</td>
                  <td>
                    <MakingPill making={k.making} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="data-line">
          {snap.contracts.length} contracts, {frozen} frozen: a contract becomes a task once frozen
        </p>
      </Block>

      <Block title="Cut from campaigns" count={CUTS.length} aside="every step, a decisive step, two steps from one state">
        <div className="tbl-wrap">
          <table className="tbl data-table data-kinds">
            <thead>
              <tr>
                <th>Cut</th>
                <th>From</th>
                <th>What it holds</th>
                <th>Trains</th>
                <th className="data-right">Now</th>
                <th>Made by</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {CUTS.map((c) => (
                <tr
                  key={c.id}
                  data-click="true"
                  data-focus={focus === `cut:${c.id}`}
                  onClick={() => go({ focus: `cut:${c.id}` })}
                  title={c.words}
                >
                  <td className="data-name">
                    {c.name}
                    {c.kind ? <span className="data-sub">kind {c.kind}</span> : null}
                  </td>
                  <td>{c.from}</td>
                  <td>{c.what}</td>
                  <td>{c.learning}</td>
                  <td className="num">
                    <Count n={c.count(snap)} />
                  </td>
                  <td>{c.madeBy}</td>
                  <td>
                    <MakingPill making={c.making} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Block>

      <Block title="Splits: by contract or family, never by scenario" count={families.length} aside="the families present">
        <div className="tbl-wrap">
          <table className="tbl data-table">
            <thead>
              <tr>
                <th>Family</th>
                <th className="data-right">Contracts</th>
                <th>Which</th>
              </tr>
            </thead>
            <tbody>
              {families.map(([family, members]) => (
                <tr key={family}>
                  <td className="data-name">{family}</td>
                  <td className="num">
                    <Count n={members.length} />
                  </td>
                  <td>
                    {members.map((c) => (
                      <button
                        key={c.id}
                        className="data-contract-link"
                        onClick={() => go({ view: "contracts", id: c.id })}
                        title={`Open ${c.id}`}
                      >
                        <StageDots stage={c.stage} /> {shortTitle(c.title)}
                      </button>
                    ))}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="data-line">
          Every contract, campaign and step of a family stays on one side of the train/test split, so no model sees
          the same design under another load case
        </p>
      </Block>
    </>
  );
}

/** The distinct families, in the order the contracts first name them, each with its contracts. */
function familiesOf<T extends { family: string }>(contracts: T[]): [string, T[]][] {
  const found = new Map<string, T[]>();
  for (const c of contracts) found.set(c.family, [...(found.get(c.family) ?? []), c]);
  return [...found.entries()];
}
