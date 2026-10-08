/**
 * Evaluations: every test of every design, a row each - the design, the scenario it was tested
 * under, the kind of test, its fidelity, each result against its limit, and the verdict. One design
 * has many evaluations; the scenario sits on every one, because the evaluation axis is where a
 * design's grades differ.
 *
 * Under it, what is real now: the scenarios each contract implies, grouped by kind - a static case
 * a torque direction, the order checks at each check speed, the mounted and free-free modes. Every
 * design of that contract will be tested under exactly these.
 */

import { shortTitle } from "../app/product";
import type { TabProps } from "../app/tab";
import { Blank, Block, StageDots } from "../panel/bits";
import type { Evaluation, Scenario } from "../records/types";
import type { Column } from "../campaigns/bits";
import { TableHead, TemplateRow, Verdict } from "../campaigns/bits";
import { DesignsHead } from "./bits";
import { evaluationVerdict, resultWords } from "./records";

const COLUMNS: Column[] = [
  { id: "design", label: "Design", template: "the design tested", min: 90 },
  {
    id: "scenario",
    label: "Scenario",
    template: "the load case, order check or support it was tested under",
    min: 160,
  },
  { id: "kind", label: "Kind", template: "static, orders or modal", min: 90 },
  { id: "fidelity", label: "Fidelity", template: "the screen, or the full TET10 proof", min: 110 },
  { id: "results", label: "Results", template: "each measure against its limit", kind: "wide", min: 180 },
  { id: "verdict", label: "Verdict", template: "pass or fail under this scenario", min: 100 },
];

const KINDS: { id: Scenario["kind"]; label: string; words: string }[] = [
  { id: "static", label: "Static", words: "a load case a torque direction" },
  { id: "orders", label: "Orders", words: "the gear orders at each check speed" },
  { id: "modal", label: "Modal", words: "free-free, and mounted once the mounts are placed" },
];

export function EvaluationsPage({ snap, route, go }: TabProps) {
  const evaluations = snap.records.evaluations;
  return (
    <div className="stage-scroll dsg-page">
      <DesignsHead snap={snap} />

      <Block title="Evaluations" count={evaluations.length} aside="one design, many tests">
        <div className="tbl-wrap">
          <table className="tbl dsg-evals">
            <TableHead columns={COLUMNS} />
            <tbody>
              {evaluations.length ? (
                evaluations.map((e) => (
                  <EvaluationRow
                    key={e.id}
                    evaluation={e}
                    focused={route.id === e.candidate}
                    onOpen={() => go({ id: e.candidate })}
                  />
                ))
              ) : (
                <TemplateRow columns={COLUMNS} />
              )}
            </tbody>
          </table>
        </div>
      </Block>

      <Block
        title="What each contract will be tested under"
        count={snap.contracts.length}
        aside="the scenarios each contract implies"
      >
        <div className="tbl-wrap">
          <table className="tbl dsg-scenarios">
            <thead>
              <tr>
                <th>Contract</th>
                {KINDS.map((k) => (
                  <th key={k.id} title={k.words}>
                    {k.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {snap.contracts.map((c) => (
                <tr key={c.id}>
                  <td>
                    <button
                      className="link"
                      onClick={() => go({ view: "contracts", id: c.id })}
                      title={`${c.title} - open the contract`}
                    >
                      {shortTitle(c.title)}
                    </button>
                    <div>
                      <StageDots stage={c.stage} /> <span className="dim">{c.scenarios.length} scenarios</span>
                    </div>
                  </td>
                  {KINDS.map((k) => (
                    <td key={k.id}>
                      <ScenarioList scenarios={c.scenarios.filter((s) => s.kind === k.id)} />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Block>

      {evaluations.length === 0 ? (
        <Blank title="Not built yet" waits="the judge and its evaluations (PHY-1 onwards)" />
      ) : null}
    </div>
  );
}

function ScenarioList({ scenarios }: { scenarios: Scenario[] }) {
  if (!scenarios.length) return <span className="dim">none</span>;
  return (
    <ul className="dsg-scenario-list">
      {scenarios.map((s) => (
        <li key={`${s.from}:${s.name}`} title={`from ${s.from}`}>
          {s.name}
        </li>
      ))}
    </ul>
  );
}

function EvaluationRow({
  evaluation: e,
  focused,
  onOpen,
}: {
  evaluation: Evaluation;
  focused: boolean;
  onOpen: () => void;
}) {
  return (
    <tr data-click="true" data-focus={focused} onClick={onOpen}>
      <td className="mono">{e.candidate}</td>
      <td>{e.scenario}</td>
      <td>{e.kind}</td>
      <td>{e.fidelity}</td>
      <td className="cmp-wide">
        <span className="dsg-results">
          {e.results.map((r) => (
            <span
              key={r.name}
              className="vs-pill"
              data-better={r.passed === true}
              data-worse={r.passed === false}
              title={r.limit === null ? "recorded, not judged" : r.passed ? "within its limit" : "over its limit"}
            >
              {resultWords(r)}
            </span>
          ))}
        </span>
      </td>
      <td>
        <Verdict passed={evaluationVerdict(e)} />
      </td>
    </tr>
  );
}
