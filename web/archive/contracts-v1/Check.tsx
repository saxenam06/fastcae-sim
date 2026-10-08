/**
 * Check: how far the contract has come, and what the validator says of it.
 *
 * The stage ladder first - posed, derived, frozen - with the one it has reached marked and what the
 * next step needs, because "why is this not a task yet" is the question this page is opened for.
 * Then what freezing it now would say, and then every rule the validator runs, each with its
 * verdict: a passed rule is listed as passed rather than left out, so the page shows the whole of
 * what was checked and not only what failed.
 */

import { useMemo } from "react";
import { STAGES } from "../app/product";
import { Block, Dot, Hash } from "../panel/bits";
import type { Refusal, Stage } from "../records/types";
import { NEXT_STEP, ruleRows } from "./model";
import type { PageProps } from "./parts";

export function Check({ snap, c, focus, go }: PageProps) {
  const rows = useMemo(() => ruleRows(snap.rules, c.refusals), [snap.rules, c]);
  const paths = useMemo(() => new Set(c.loaded ? c.entries.map((e) => e.path) : []), [c]);
  const onFocus = (path: string) => go({ id: c.id, focus: path });
  const refused = rows.filter((r) => r.refusals.length > 0).length;
  const summary = `${rows.length} rules · ${
    !c.loaded
      ? "refused at load, the others not run"
      : refused
        ? `${rows.length - refused} passed · ${refused} refused`
        : "all passed"
  }`;

  return (
    <div className="stage-scroll ct-page">
      {c.loaded ? (
        <>
          <Block title="Stage">
            <Ladder stage={c.stage} />
            <p className="ct-next">
              {c.stage === "frozen" ? (
                <>
                  <Dot status="done" /> frozen: <Hash value={c.frozen_hash} />
                </>
              ) : (
                <>
                  <Dot status={c.stage === "posed" ? "blank" : "pending"} /> next: {NEXT_STEP[c.stage]}
                </>
              )}
            </p>
          </Block>

          <Block title="Freezing it now">
            {c.stage === "frozen" ? (
              <p className="ct-next">
                <Dot status="done" /> frozen already: its hash is the task's identity
              </p>
            ) : c.freeze.ready ? (
              <p className="ct-next">
                <Dot status="done" /> ready: the validator accepts it frozen
              </p>
            ) : (
              <>
                <p className="ct-next">
                  <Dot status="failed" /> refused <span className="num">{c.freeze.refusals.length}</span>
                </p>
                <div className="tbl-wrap">
                  <table className="tbl">
                    <thead>
                      <tr>
                        <th>rule</th>
                        <th>entry</th>
                        <th>reason</th>
                      </tr>
                    </thead>
                    <tbody>
                      {c.freeze.refusals.map((r, i) => (
                        <tr key={i}>
                          <td className="mono">{r.rule}</td>
                          <td>
                            <EntryRef r={r} paths={paths} focus={focus} onFocus={onFocus} />
                          </td>
                          <td>{r.reason}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </Block>
        </>
      ) : (
        <Block title="Stage">
          <p className="ct-next">
            <Dot status="failed" /> does not load: the validator refuses the file before it reads a stage
          </p>
        </Block>
      )}

      <Block title="Validator rules" aside={summary}>
        <div className="tbl-wrap">
          <table className="tbl ct-rules">
            <thead>
              <tr>
                <th aria-label="verdict" />
                <th>rule</th>
                <th>what it checks</th>
                <th>refusals</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(({ rule, refusals }) => {
                const ran = c.loaded || refusals.length > 0;
                const status = refusals.length ? "failed" : ran ? "done" : "pending";
                return (
                  <tr key={rule.id} data-refused={refusals.length > 0}>
                    <td className="ct-dot-cell">
                      <Dot status={status} title={refusals.length ? "refused" : ran ? "passed" : "not run"} />
                    </td>
                    <td className="mono ct-rule-id">{rule.id}</td>
                    <td>{rule.words || <span className="dim">not in the snapshot's rule list</span>}</td>
                    <td>
                      {refusals.length ? (
                        refusals.map((r, i) => (
                          <div key={i} className="ct-refusal">
                            <EntryRef r={r} paths={paths} focus={focus} onFocus={onFocus} />
                            <span> · {r.reason}</span>
                          </div>
                        ))
                      ) : (
                        <span className="dim">{ran ? "passed" : "not run"}</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Block>
    </div>
  );
}

/** The three stages in a row, the one reached marked, each with what it means. */
function Ladder({ stage }: { stage: Stage }) {
  const reached = STAGES.findIndex((s) => s.id === stage);
  return (
    <ol className="ct-ladder">
      {STAGES.map((s, i) => (
        <li key={s.id} data-reached={i <= reached} data-current={i === reached} data-stage={s.id}>
          <div className="ct-ladder-head">
            <i className="ct-ladder-mark" />
            <b>{s.label}</b>
            {i === reached ? <span className="ct-now">now</span> : null}
          </div>
          <p>{s.words}</p>
        </li>
      ))}
    </ol>
  );
}

/** A refusal's entry: a link to it when it is an entry of this contract, its name as text otherwise. */
function EntryRef({
  r,
  paths,
  focus,
  onFocus,
}: {
  r: Refusal;
  paths: Set<string>;
  focus: string | null;
  onFocus: (path: string) => void;
}) {
  if (!r.entry) return <span className="dim">-</span>;
  if (!paths.has(r.entry)) return <span className="mono">{r.entry}</span>;
  return (
    <button
      className="link mono"
      data-focus={focus === r.entry}
      onClick={() => onFocus(r.entry)}
      title="Open it in the card"
    >
      {r.entry}
    </button>
  );
}
