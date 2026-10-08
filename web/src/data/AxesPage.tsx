/**
 * Axes: the four axes every datapoint sits on - task, attempt, evaluation, result (data design §3).
 *
 * Side by side, because the point is the test between them: does the engineer require a quantity,
 * does the judge test under it, or does it come out? Each box says what its axis answers, a few
 * examples, and what the record holds on it now. The evaluation axis is the one with real content
 * today: every contract already implies the scenarios its designs will be judged under, and the
 * table under the boxes lists them contract by contract.
 */

import type { ReactNode } from "react";
import { shortTitle } from "../app/product";
import type { TabProps } from "../app/tab";
import { Block, Count, Dot, StageDots } from "../panel/bits";
import type { ContractView, Scenario } from "../records/types";

const SCENARIO_KINDS: { id: Scenario["kind"]; label: string }[] = [
  { id: "static", label: "static" },
  { id: "orders", label: "orders" },
  { id: "modal", label: "modal" },
];

const scenariosOf = (c: ContractView, kind: Scenario["kind"]) => c.scenarios.filter((s) => s.kind === kind);

export function AxesPage({ snap, go }: TabProps) {
  const r = snap.records;
  const scenarios = snap.contracts.reduce((n, c) => n + c.scenarios.length, 0);
  const results = r.evaluations.reduce((n, e) => n + e.results.length, 0);
  return (
    <>
      <div className="data-axes">
        <Axis
          name="Task"
          sub="the contract"
          answers="What must the design meet?"
          examples="peak torque, ratio, mounts, package, limits"
          full="The required peak torque, ratio, mounts, package, process, limits, priorities"
          inData="a change gives a new contract, so a new task"
        >
          {snap.contracts.map((c) => (
            <button
              key={c.id}
              className="data-axis-row"
              onClick={() => go({ view: "contracts", id: c.id })}
              title={`Open ${c.id}`}
            >
              <StageDots stage={c.stage} />
              <span>{shortTitle(c.title)}</span>
            </button>
          ))}
        </Axis>

        <Axis
          name="Attempt"
          answers="What was tried?"
          examples="campaign → hypothesis → design"
          full="Campaign → hypothesis → design"
          inData="many per contract"
        >
          <dl className="data-axis-kv">
            <dt>campaigns</dt>
            <dd>
              <Count n={r.campaigns.length} />
            </dd>
            <dt>hypotheses</dt>
            <dd>
              <Count n={r.episodes.length} />
            </dd>
            <dt>designs</dt>
            <dd>
              <Count n={r.candidates.length} />
            </dd>
          </dl>
          <p className="data-axis-waits">
            <Dot status="blank" /> the agent (AGT), the geometry (GEO-1)
          </p>
        </Axis>

        <Axis
          name="Evaluation"
          sub="the scenarios"
          answers="Under which conditions is the design tested?"
          examples="drive, regeneration, reverse; mounted or free-free; check speeds"
          full="The load cases (drive, regeneration, reverse, park lock), hot and cold, mounted or free-free, the order-check speeds, screen or full FE, mesh size"
          inData="one design, many evaluation records"
        >
          {snap.contracts.map((c) => (
            <div key={c.id} className="data-axis-contract">
              <div className="data-axis-title" title={c.title}>
                {shortTitle(c.title)}
              </div>
              <div className="pills">
                {SCENARIO_KINDS.map((k) => {
                  const these = scenariosOf(c, k.id);
                  return (
                    <span key={k.id} className="pill" title={these.map((s) => s.name).join("\n") || "none"}>
                      {k.label} <b className="num">{these.length}</b>
                    </span>
                  );
                })}
              </div>
            </div>
          ))}
        </Axis>

        <Axis
          name="Result"
          answers="What did the test show?"
          examples="misalignment, tilt, modes, mass, the verdict"
          full="Displacements, misalignment, tilt, stress, natural frequencies, mode shapes, mass, the verdict with margins"
          inData="what the physics models learn to predict"
        >
          <div className="data-axis-big">
            <Count n={results} /> <span className="dim">nothing judged yet</span>
          </div>
          <p className="data-axis-waits">
            <Dot status="blank" /> the judge (PHY-1)
          </p>
        </Axis>
      </div>

      <p className="data-test">
        The test: does the engineer <b>require</b> it (task), does the judge <b>test under</b> it (evaluation), or
        does it <b>come out</b> (result)?
      </p>
      <div className="pills data-test-pills">
        <span
          className="pill"
          title="The required torque is a task input: the best design changes with it. Applying it in drive, regeneration and reverse is an evaluation"
        >
          torque sits on two axes
        </span>
        <span
          className="pill"
          title="Mode shapes come out of the modal scenario, whose supports (mounted or free-free) sit on the evaluation axis; the modal requirement (at least 3 % from gear orders at the check speeds) is in the contract's limits"
        >
          mode shapes are results
        </span>
      </div>

      <Block title="The evaluation axis, contract by contract" count={scenarios} aside="what each contract implies">
        <div className="tbl-wrap">
          <table className="tbl data-scenarios">
            <thead>
              <tr>
                <th>Contract</th>
                {SCENARIO_KINDS.map((k) => (
                  <th key={k.id}>{k.label}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {snap.contracts.map((c) => (
                <tr key={c.id}>
                  <td>
                    <span className="data-scenario-contract">
                      <StageDots stage={c.stage} /> {shortTitle(c.title)}
                    </span>
                  </td>
                  {SCENARIO_KINDS.map((k) => (
                    <td key={k.id}>
                      {scenariosOf(c, k.id).map((s) => (
                        <div key={s.name} className="data-scenario" title={`from ${s.from}`}>
                          {s.name}
                        </div>
                      ))}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="data-line">
          One design gives one evaluation record per scenario; splits are by contract or family, never by scenario
        </p>
      </Block>
    </>
  );
}

function Axis({
  name,
  sub,
  answers,
  examples,
  full,
  inData,
  children,
}: {
  name: string;
  sub?: string;
  answers: string;
  /** A few examples, and the data design's whole list for the hover. */
  examples: string;
  full: string;
  inData: string;
  children: ReactNode;
}) {
  return (
    <section className="data-axis">
      <header className="data-axis-head">
        <h3>
          {name}
          {sub ? <span className="dim"> ({sub})</span> : null}
        </h3>
        <p className="data-axis-answers">{answers}</p>
      </header>
      <dl className="data-axis-about">
        <dt>e.g.</dt>
        <dd title={full}>{examples}</dd>
        <dt>in data</dt>
        <dd>{inData}</dd>
      </dl>
      <div className="data-axis-now">
        <div className="data-axis-now-head">now</div>
        {children}
      </div>
    </section>
  );
}
