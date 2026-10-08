/**
 * The contract page: one contract, as a product shows it.
 *
 * Top to bottom, in the order an engineer reads a task:
 * - the head: what it is, where it stands (posed, derived, frozen), the checks;
 * - inputs: what the user gives, grouped, each value in its box with its source in two words;
 * - calculations: what the tools work out from them, each with its method pre-selected and the
 *   function that runs it; planned ones say which tool will;
 * - pass criteria: what a design must meet, each with its standard;
 * - the design to beat: the published numbers;
 * - the assumptions, folded: what is still to confirm.
 *
 * Nothing here is prose about the contract. Full citations wait on hover.
 */

import { shortTitle, STAGES } from "../app/product";
import { Dot } from "../panel/bits";
import type { ContractView, InputGroup, Snapshot } from "../records/types";
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

        <Section title="Inputs" aside={`${inputs.length} values · ${assumed} assumed`}>
          <div className="cp-groups">
            {page.inputs.map((g) => (
              <Group key={g.group} g={g} />
            ))}
          </div>
        </Section>

        <Section title="Calculations" aside={`${computed} computed · ${page.calculations.length - computed} planned`}>
          <table className="cp-table cp-calcs">
            <thead>
              <tr>
                <th>Quantity</th>
                <th>Method</th>
                <th>Result</th>
              </tr>
            </thead>
            <tbody>
              {page.calculations.map((c) => (
                <tr key={c.quantity} data-status={c.status}>
                  <th>{c.quantity}</th>
                  <td>
                    <Method method={c.method} by={c.by} fn={c.function} />
                    <div className="cp-fn mono">{c.function}</div>
                  </td>
                  <td className="cp-result">
                    <Dot status={c.status === "computed" ? "done" : "blank"} /> {c.result}
                  </td>
                </tr>
              ))}
            </tbody>
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
      ? "Next: derive the interfaces and loads (the load tool, GBX-1)"
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
  // In the stage table, a source is marked only where it differs from the table's own.
  const cells = table?.rows.flatMap((r) => r.cells) ?? [];
  const common = mostCommon(cells.map((c) => c.source));
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
              {table.columns.map((c) => (
                <th key={c}>{c}</th>
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
                    {c.source !== common ? (
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
          {common ? (
            <caption>
              From <b>{common}</b> unless marked
            </caption>
          ) : null}
        </table>
      ) : null}
    </div>
  );
}

function mostCommon(values: string[]): string {
  const counts = new Map<string, number>();
  for (const v of values) if (v) counts.set(v, (counts.get(v) ?? 0) + 1);
  let best = "";
  for (const [v, n] of counts) if (!best || n > (counts.get(best) ?? 0)) best = v;
  return best;
}
