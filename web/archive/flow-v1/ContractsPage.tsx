/**
 * Contracts through the factory: where each contract is on its way to data.
 *
 * First the factory as a chain of boxes, so the whole line is seen before any row of it. Then the
 * matrix, the heart of the tab: a contract a row and a stage a column, so a contract's progress
 * reads left to right and a stage's reach reads top to bottom. The columns after "frozen" are all
 * 0 today and are drawn faint, not hidden: they are where the agent, the geometry, the judge and
 * the record will write, and the empty columns say so.
 */

import { shortTitle } from "../app/product";
import type { TabProps } from "../app/tab";
import { Block, Count, Dot, Hash, StageDots } from "../panel/bits";
import { KINDS } from "../data/kinds";
import type { ContractView, Snapshot } from "../records/types";
import {
  GROUPS,
  maker,
  noun,
  STAGES,
  stageDot,
  stagesIn,
  stageStatus,
  STATUS_WORDS,
  type FactoryStage,
} from "./stages";
import { tallyContracts, type ContractTally } from "./tally";

export function ContractsPage({ snap, route, go }: TabProps) {
  const rows = tallyContracts(snap);
  return (
    <>
      <Block title="The factory" aside="requirement to datapoint">
        <Chain snap={snap} focus={route.focus} onFocus={(id) => go({ focus: id })} />
      </Block>
      <Totals snap={snap} />
      <Block title="Contracts by stage" count={rows.length} aside="a row opens the contract">
        <div className="tbl-wrap">
          <table className="tbl flow-matrix">
            <thead>
              <tr className="flow-groups">
                <th rowSpan={2} className="flow-corner">
                  Contract
                </th>
                {GROUPS.map((g) => (
                  <th key={g.id} colSpan={stagesIn(g.id).length} className="flow-group" title={g.words}>
                    {g.label}
                  </th>
                ))}
              </tr>
              <tr>
                {STAGES.map((s) => (
                  <ColumnHead
                    key={s.id}
                    stage={s}
                    snap={snap}
                    focused={route.focus === s.id}
                    onFocus={() => go({ focus: s.id })}
                  />
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <ContractRow
                  key={row.contract.id}
                  row={row}
                  onOpen={() => go({ view: "contracts", id: row.contract.id })}
                />
              ))}
            </tbody>
          </table>
        </div>
        <p className="flow-waits">
          <Dot status="blank" /> Campaigns onward fill when the agent (AGT), the geometry (GEO-1), the judge
          (PHY-1) and the record (DAT-1) are built
        </p>
      </Block>
    </>
  );
}

/** The stages as boxes in a row, a group a cluster, wrapping between clusters when narrow. */
function Chain({ snap, focus, onFocus }: { snap: Snapshot; focus: string | null; onFocus: (id: string) => void }) {
  return (
    <div className="flow-chain">
      {GROUPS.map((g, gi) => {
        const stages = stagesIn(g.id);
        return (
          <div key={g.id} className="flow-chain-group">
            <div className="flow-chain-caption" title={g.words}>
              {g.label}
            </div>
            <div className="flow-chain-row">
              {stages.map((s, si) => {
                const n = s.count(snap);
                const status = stageStatus(s, n);
                const last = gi === GROUPS.length - 1 && si === stages.length - 1;
                return (
                  <span key={s.id} className="flow-chain-cell">
                    <button
                      className="flow-chain-box"
                      data-built={s.built}
                      data-focus={focus === s.id}
                      onClick={() => onFocus(s.id)}
                      title={`${s.label}: ${s.what}. Made by ${maker(s, snap)}; ${STATUS_WORDS[status]}`}
                    >
                      <span className="flow-chain-label">
                        <Dot status={stageDot(status)} />
                        {s.label}
                      </span>
                      <span className="flow-chain-count">
                        <Count n={n} /> {noun(s, n)}
                      </span>
                      <span className="flow-chain-mark">{s.built ? "built" : "not built"}</span>
                    </button>
                    {last ? null : <span className="flow-chain-arrow">→</span>}
                  </span>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}

/** One line of what the factory holds now. */
function Totals({ snap }: { snap: Snapshot }) {
  const count = (id: string) => STAGES.find((s) => s.id === id)?.count(snap) ?? 0;
  const ready = snap.contracts.filter((c) => c.stage !== "frozen" && c.freeze.ready).length;
  const items: [number, string][] = [
    [snap.contracts.length, "contracts"],
    [count("derived"), "derived"],
    [count("frozen"), "frozen"],
    [ready, "ready to freeze"],
    [count("campaign"), "campaigns"],
    [count("design"), "designs"],
    [count("grade"), "grades"],
    [count("datapoints"), "datapoints"],
  ];
  return (
    <div className="flow-totals">
      {items.map(([n, label]) => (
        <span key={label}>
          <Count n={n} /> {label}
        </span>
      ))}
    </div>
  );
}

function ColumnHead({
  stage,
  snap,
  focused,
  onFocus,
}: {
  stage: FactoryStage;
  snap: Snapshot;
  focused: boolean;
  onFocus: () => void;
}) {
  const status = stageStatus(stage, stage.count(snap));
  return (
    <th
      className="flow-col"
      data-first={stagesIn(stage.group)[0] === stage}
      data-built={stage.built}
      data-focus={focused}
    >
      <button onClick={onFocus} title={`${stage.label}: ${stage.what} - ${STATUS_WORDS[status]}`}>
        <Dot status={stageDot(status)} />
        <span>{stage.column}</span>
      </button>
    </th>
  );
}

function ContractRow({ row, onOpen }: { row: ContractTally; onOpen: () => void }) {
  const c = row.contract;
  return (
    <tr data-click="true" onClick={onOpen} title={`Open ${c.id}`}>
      <th scope="row" className="flow-row-head">
        <div className="flow-row-grid">
          <StageDots stage={c.stage} />
          <span className="flow-row-title">{shortTitle(c.title)}</span>
          <span className="flow-row-family" title={c.family}>
            {c.family}
          </span>
        </div>
      </th>
      {STAGES.map((s) => (
        <td
          key={s.id}
          className="flow-cell"
          data-first={stagesIn(s.group)[0] === s}
          data-built={s.built}
        >
          <Cell stage={s} row={row} />
        </td>
      ))}
    </tr>
  );
}

function Cell({ stage, row }: { stage: FactoryStage; row: ContractTally }) {
  const c = row.contract;
  switch (stage.id) {
    case "requirement":
      return (
        <span title={`${row.citations} cited sources`}>
          <Count n={row.citations} />
        </span>
      );
    case "posed":
      return <Posed contract={c} />;
    case "derived":
      return c.stage === "derived" || c.stage === "frozen" ? (
        <span className="flow-tick" title="interfaces and physics present">
          ✓
        </span>
      ) : (
        <span className="dim">–</span>
      );
    case "frozen":
      return <Frozen contract={c} />;
    case "datapoints":
      return (
        <span className="flow-dp" title="datapoints by kind">
          {KINDS.map((k) => (
            <span key={k.letter} title={`${k.letter}: ${k.name}`}>
              <i>{k.letter}</i>
              <Count n={k.perContract(row)} />
            </span>
          ))}
        </span>
      );
    default:
      return <Count n={stage.perContract(row)} />;
  }
}

function Posed({ contract }: { contract: ContractView }) {
  if (!contract.loaded || contract.refusals.length) {
    const n = contract.refusals.length;
    return (
      <span className="flow-refused" title={contract.refusals.map((r) => `${r.rule}: ${r.reason}`).join("\n")}>
        ✗ {n} {n === 1 ? "refusal" : "refusals"}
      </span>
    );
  }
  return (
    <span className="flow-tick" title="the validator accepts it">
      ✓
    </span>
  );
}

function Frozen({ contract }: { contract: ContractView }) {
  if (contract.frozen_hash) return <Hash value={contract.frozen_hash} />;
  if (contract.freeze.ready) {
    return (
      <span className="pill flow-ready" title="the validator would accept it frozen now">
        ready
      </span>
    );
  }
  const why = contract.freeze.refusals.map((r) => r.reason).join("; ");
  return (
    <span className="dim" title={why ? `not ready: ${why}` : "not ready"}>
      –
    </span>
  );
}
