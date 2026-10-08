/**
 * The verdict each contract sets: a compact card a contract, read from the snapshot - every entry
 * of its limits layer with its value and where it came from, then what is optimised and what is
 * only recorded. This is real today: it is what every design of that contract will be graded
 * against, whether or not any design exists.
 *
 * Side by side, because the contracts share most of their limits and differ in a few (the check
 * speeds, above all); a row a limit lets the eye run across. A click on a limit opens it in the
 * contract.
 */

import { OBJECTIVE, shortTitle } from "../app/product";
import type { Go } from "../app/route";
import { Prov, StageDots } from "../panel/bits";
import type { ContractView, EntryView, Snapshot } from "../records/types";

export function VerdictCards({ snap, go }: { snap: Snapshot; go: Go }) {
  return (
    <div className="dsg-verdicts">
      {snap.contracts.map((c) => (
        <VerdictCard key={c.id} contract={c} go={go} />
      ))}
    </div>
  );
}

function VerdictCard({ contract, go }: { contract: ContractView; go: Go }) {
  const limits = contract.entries.filter((e) => e.layer === "limits");
  return (
    <section className="dsg-vcard">
      <header>
        <button
          className="link"
          onClick={() => go({ view: "contracts", id: contract.id })}
          title={`${contract.title} - open the contract`}
        >
          {shortTitle(contract.title)}
        </button>
        <StageDots stage={contract.stage} />
      </header>
      <div className="dsg-vrule dim mono" title="the version of the rule that turns these limits into a verdict">
        verdict rule {contract.verdict_rule_version}
      </div>
      {limits.length ? (
        groups(limits).map(([group, entries]) => (
          <div key={group} className="dsg-vgroup">
            <div className="dsg-vgroup-name">{group}</div>
            {entries.map((e) => (
              <button
                key={e.path}
                className="dsg-limit"
                onClick={() => go({ view: "contracts", id: contract.id, focus: e.path })}
                title={`${e.path}${e.provenance.citation ? `\n${e.provenance.citation}` : ""}${
                  e.provenance.assumption_id ? `\nassumption ${e.provenance.assumption_id}` : ""
                }`}
              >
                <span className="dsg-limit-label">{e.label}</span>
                <span className="mono">{e.value}</span>
                <Prov kind={e.provenance.kind} />
              </button>
            ))}
          </div>
        ))
      ) : (
        <div className="dsg-vgroup dim">no limits yet</div>
      )}
      <dl className="dsg-vfoot">
        <dt>objective</dt>
        <dd>{OBJECTIVE[contract.objective] ?? contract.objective}</dd>
        <dt>stress</dt>
        <dd>{contract.stress === "recorded" ? "recorded, not judged" : contract.stress}</dd>
      </dl>
    </section>
  );
}

/** Entries by their group on the sheet, in the order the contract lists them. */
function groups(entries: EntryView[]): [string, EntryView[]][] {
  const out = new Map<string, EntryView[]>();
  for (const e of entries) out.set(e.group, [...(out.get(e.group) ?? []), e]);
  return [...out];
}
