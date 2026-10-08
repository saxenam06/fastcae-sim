/**
 * The contract page: one contract, as a product shows it.
 *
 * Top to bottom, in the order an engineer reads a task:
 * - the head: what it is, where it stands (posed, derived, frozen), the checks;
 * - inputs: only what is given or assumed, grouped, each value in its box with its source in two
 *   words;
 * - calculated: the calculation chain's steps, each with its method pre-selected and the function
 *   that runs it, what it takes in (an input, or another step's output) and what it gives out;
 *   planned ones say which PBI builds them;
 * - pass criteria: what a design must meet, each with its standard;
 * - the design to beat: the published numbers;
 * - the assumptions, folded: what is still to confirm.
 *
 * Nothing here is prose about the contract. Full citations wait on hover.
 */

import { shortTitle, STAGES } from "../app/product";
import { Dot } from "../panel/bits";
import type { Calculation, ContractView, InputGroup, Snapshot, StepInput, StepTable } from "../records/types";
import { Method, Section, Source, Value } from "../panel/page";

export function ContractPage({ contract, snap }: { contract: ContractView; snap: Snapshot }) {
  const page = contract.page;
  const computed = page.calculations.filter((c) => c.status === "computed").length;
  const inputs = page.inputs.flatMap((g) => [...g.rows, ...(g.table?.rows.flatMap((r) => r.cells) ?? [])]);
  const assumed = inputs.filter((r) => r.kind === "assumption").length;
  return (
    <div className="stage-scroll cp-scroll">
      <div className="cp-page">
        <Head contract={contract} rules={snap.rules.length} />

        <Section title="Inputs" aside={`your requirements · ${inputs.length} values, ${assumed} assumed`}>
          <div className="cp-groups">
            {page.inputs.map((g) => (
              <Group key={g.group} g={g} />
            ))}
          </div>
        </Section>

        <Section
          title="Calculated"
          aside={`what zenryx works out from them, step by step · ${computed} computed, ${page.calculations.length - computed} planned`}
        >
          <table className="cp-table cp-calcs">
            <thead>
              <tr>
                <th>#</th>
                <th>Step</th>
                <th>Method</th>
                <th>Takes in</th>
                <th>Gives out</th>
              </tr>
            </thead>
            <tbody>
              {page.calculations.map((c) => (
                <tr key={c.step} data-status={c.status}>
                  <td className="cp-step-n">
                    <b title={c.status}>{c.step}</b>
                  </td>
                  <th>{c.quantity}</th>
                  <td>
                    <Method method={c.method} by={c.by} fn={c.function} />
                    {/* A function's name may break after a dot, so the column stays narrow. */}
                    <div className="cp-fn mono">{c.function.replace(/\./g, ".​")}</div>
                  </td>
                  <td className="cp-takes">
                    <TakesIn items={c.takes_in} steps={page.calculations} />
                  </td>
                  <td className="cp-gives">{c.table ? <StepOut t={c.table} /> : <Planned c={c} />}</td>
                </tr>
              ))}
            </tbody>
            <caption>
              Each step names what it takes: inputs from above, and other steps' outputs under the step they
              come from. Steps 5, 6 and 7 go round, from a first guess, until the bearing sizes stop changing.
            </caption>
          </table>
        </Section>

        <div className="cp-pair">
          <Section title="Pass criteria">
            <table className="cp-table">
              <tbody>
                {page.criteria.map((c) => (
                  <tr key={c.label}>
                    <th>{c.label}</th>
                    <td>{c.value}</td>
                    <td className="cp-src">
                      <Source s={c} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Section>

          <Section title="The design to beat" aside="published">
            <div className="cp-beat">
              {page.to_beat.map((b) => (
                <div key={b.quantity} className="cp-beat-item" data-warn={b.note !== ""}>
                  <div className="cp-beat-q">{b.quantity}</div>
                  <div className="cp-beat-v mono">{b.value}</div>
                  {b.note ? <div className="cp-beat-note">⚠ {b.note}</div> : null}
                  <span className="prov" data-prov="published" title={b.title}>
                    {b.source}
                  </span>
                </div>
              ))}
            </div>
          </Section>
        </div>

        <details className="cp-assumptions">
          <summary>
            {contract.assumptions.length} assumptions to confirm
          </summary>
          <ul>
            {contract.assumptions.map((a) => (
              <li key={a.id}>
                <b className="mono">{a.id}</b> <span className="cp-a-what">{a.what}</span>
                <span className="cp-a-value">{a.value}</span>
                <span className="dim">{a.why}</span>
              </li>
            ))}
          </ul>
        </details>
      </div>
    </div>
  );
}

function Head({ contract, rules }: { contract: ContractView; rules: number }) {
  const reached = STAGES.findIndex((s) => s.id === contract.stage);
  const refused = contract.refusals.length;
  const next =
    contract.stage === "posed"
      ? "Next: derive the seats and loads (the load tool, GBX-1 to GBX-4)"
      : contract.stage === "derived"
        ? "Next: freeze it into a task"
        : "Frozen: ready for campaigns";
  return (
    <header className="cp-head">
      <div className="cp-head-main">
        <div className="cp-kicker">Contract</div>
        <h1>{shortTitle(contract.title)}</h1>
        <div className="cp-sub">
          {contract.family} · {contract.level}
        </div>
      </div>
      <div className="cp-head-side">
        <ol className="cp-ladder" aria-label="stage">
          {STAGES.map((s, i) => (
            <li key={s.id} data-reached={i <= reached} data-current={i === reached} title={s.words}>
              <i />
              {s.label}
            </li>
          ))}
        </ol>
        <div className="cp-badges">
          <span className="cp-badge" data-ok={refused === 0}>
            {refused === 0 ? `✓ ${rules} checks passed` : `${refused} refused`}
          </span>
          <span className="cp-badge" data-tone="next">
            {next}
          </span>
        </div>
      </div>
    </header>
  );
}

function Group({ g }: { g: InputGroup }) {
  const table = g.table ?? null;
  return (
    <div className="cp-card" data-wide={table !== null}>
      <h3>{g.group}</h3>
      <table className="cp-inputs">
        <tbody>
          {g.rows.map((r) => (
            <tr key={r.label}>
              <th>{r.label}</th>
              <td>
                <Value value={r.value} options={r.options} />
                {r.detail ? <div className="cp-detail mono">{r.detail}</div> : null}
              </td>
              <td className="cp-src">
                <Source s={r} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {table ? (
        <table className="cp-table cp-stages">
          <thead>
            <tr>
              <th />
              {table.columns.map((c, i) => (
                <th key={c}>
                  {c}
                  {table.sources[i]?.source ? (
                    <>
                      {" · "}
                      <Source s={table.sources[i]} />
                    </>
                  ) : null}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {table.rows.map((r) => (
              <tr key={r.label}>
                <th>{r.label}</th>
                {r.cells.map((c, i) => (
                  <td key={i}>
                    <Value value={c.value} />
                    {c.own ? (
                      <>
                        {" "}
                        <Source s={c} />
                      </>
                    ) : null}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
    </div>
  );
}

/** What a step takes in, each by name, grouped by where it comes from: the inputs above, or a
 * step's output, under that step's number and name. */
function TakesIn({ items, steps }: { items: StepInput[]; steps: Calculation[] }) {
  const groups = new Map<number, string[]>();
  for (const t of items) {
    const key = t.step ?? 0; // 0: the inputs above
    groups.set(key, [...(groups.get(key) ?? []), t.name]);
  }
  const keys = [...groups.keys()].sort((a, b) => a - b);
  const named = (k: number) => steps.find((s) => s.step === k)?.quantity.toLowerCase() ?? "";
  return (
    <>
      {keys.map((k) => (
        <div key={k} className="cp-takes-group" data-from={k === 0 ? "input" : "step"}>
          <div className="cp-takes-from">{k === 0 ? "Inputs" : `From step ${k}, ${named(k)}`}</div>
          {groups.get(k)?.map((name) => (
            <span key={name} className="cp-in">
              {name}
            </span>
          ))}
        </div>
      ))}
    </>
  );
}

/** What a computed step gave: a row a quantity, a column a stage where it has one. */
function StepOut({ t }: { t: StepTable }) {
  return (
    <table className="cp-out" data-cols={t.columns.length > 0}>
      {t.columns.length ? (
        <thead>
          <tr>
            <th />
            {t.columns.map((c) => (
              <th key={c}>{c}</th>
            ))}
          </tr>
        </thead>
      ) : null}
      <tbody>
        {t.rows.map((r) => (
          <tr key={r.label}>
            <th>{r.label}</th>
            {r.cells.map((cell, i) => (
              <td key={i}>{cell}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/** A step still to build: what it will give, and the PBI that builds it. */
function Planned({ c }: { c: Calculation }) {
  return (
    <div className="cp-planned">
      <Dot status="blank" /> {c.gives}
      <div className="cp-plan">planned · {c.plan}</div>
    </div>
  );
}
