/**
 * The rail: every contract, grouped by how far it has come - frozen, derived, posed.
 *
 * Frozen comes first because a frozen contract is a task a campaign can attempt; posed last, because
 * it is still a requirement waiting for its derivation. Every group is drawn even when empty, so the
 * three stages always read as one ladder and an empty one says plainly that nothing has reached it.
 * A row is fastcae's campaign row: the short title, the family under it, the stage dots, the
 * validator's verdict, and the hash once frozen.
 */

import { useMemo } from "react";
import { STAGES, shortTitle } from "../app/product";
import type { TabProps } from "../app/tab";
import { Hash, StageDots } from "../panel/bits";
import type { ContractView } from "../records/types";
import { RAIL_ORDER, contractIn, resolves } from "./model";
import { VerdictChip } from "./parts";

export function Rail({ snap, route, go }: TabProps) {
  const current = contractIn(snap, route.id);
  const groups = useMemo(() => {
    const staged = RAIL_ORDER.map((stage) => ({
      stage,
      spec: STAGES.find((s) => s.id === stage) ?? STAGES[0],
      contracts: snap.contracts.filter((c) => c.loaded && c.stage === stage),
    }));
    return { staged, unloaded: snap.contracts.filter((c) => !c.loaded) };
  }, [snap.contracts]);

  // Opening another contract keeps the entry in focus when that contract has it too, so one value
  // can be read across contracts; otherwise the card shows the contract itself.
  const open = (c: ContractView) => go({ id: c.id, focus: resolves(c, route.focus) ? route.focus : null });

  return (
    <nav className="pipeline ct-rail">
      <header className="pipeline-head">
        <span>Contracts</span>
        <span className="count">{snap.contracts.length}</span>
      </header>
      {groups.staged.map(({ stage, spec, contracts }) => (
        <section key={stage} className="rail-group">
          <header title={spec.words}>
            <span className="ct-rail-stage-name">{spec.label}</span>
            <span className="count">{contracts.length}</span>
          </header>
          {contracts.length ? (
            contracts.map((c) => (
              <ContractRow key={c.id} c={c} active={c.id === current?.id} onOpen={() => open(c)} />
            ))
          ) : (
            <div className="rail-note ct-rail-none">none</div>
          )}
        </section>
      ))}
      {groups.unloaded.length ? (
        <section className="rail-group">
          <header title="The validator refuses the file before it reads its entries">
            <span className="ct-rail-stage-name">does not load</span>
            <span className="count">{groups.unloaded.length}</span>
          </header>
          {groups.unloaded.map((c) => (
            <button
              key={c.id}
              className="campaign-row ct-rail-row"
              data-active={c.id === current?.id}
              onClick={() => go({ id: c.id, focus: null })}
              title={c.file}
            >
              <span className="ct-rail-top">
                <span className="campaign-name mono">{c.id}</span>
                <VerdictChip c={c} />
              </span>
              <span className="ct-rail-family">{c.file}</span>
            </button>
          ))}
        </section>
      ) : null}
      <p className="rail-note ct-rail-foot">
        A contract is posed from a published requirement, derived by the tools, then frozen: its hash is the
        task's identity.
      </p>
    </nav>
  );
}

function ContractRow({ c, active, onOpen }: { c: ContractView; active: boolean; onOpen: () => void }) {
  return (
    <button className="campaign-row ct-rail-row" data-active={active} onClick={onOpen} title={c.title}>
      <span className="ct-rail-top">
        <span className="campaign-name">{shortTitle(c.title)}</span>
        <VerdictChip c={c} />
      </span>
      <span className="ct-rail-family">{c.family}</span>
      <span className="ct-rail-stage">
        <StageDots stage={c.stage} />
        <span className="dim">{c.stage}</span>
        {c.frozen_hash ? <Hash value={c.frozen_hash} /> : null}
      </span>
    </button>
  );
}
