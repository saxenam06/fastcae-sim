/**
 * The Campaigns rail: a group a contract, its campaigns under it, as fastcae's campaign rail lists
 * them - a row each, with who attempted it, the budget spent of the total, how it stopped, and a
 * dot a design.
 *
 * Grouped by contract because a campaign is one attempt at one task, and the task is the contract:
 * the question "what has been tried on this?" is answered by reading down one group. Above the
 * groups, the counts that decide whether any campaign can start: the frozen contracts and the ones
 * ready to freeze, named.
 */

import { STAGES, shortTitle } from "../app/product";
import type { TabProps } from "../app/tab";
import { Count, StageDots } from "../panel/bits";
import type { Campaign, ContractView } from "../records/types";
import { campaignsOf, candidatesOf, frozen, inView, readyToFreeze } from "./records";
import { ARM, STOP } from "./words";

export function CampaignsRail(props: TabProps) {
  const { snap, route, go } = props;
  const { campaign, contract } = inView(snap, route);
  const open = (c: ContractView) => go({ view: "contracts", id: c.id });
  return (
    <nav className="cmp-rail">
      <div className="rail-note">A campaign attempts a frozen contract</div>
      <dl className="kv cmp-counts">
        <dt>frozen</dt>
        <dd>
          <Named contracts={frozen(snap)} onOpen={open} />
        </dd>
        <dt>ready to freeze</dt>
        <dd>
          <Named contracts={readyToFreeze(snap)} onOpen={open} />
        </dd>
      </dl>
      {snap.contracts.map((c) => (
        <ContractGroup
          key={c.id}
          {...props}
          contract={c}
          focused={contract?.id === c.id}
          active={campaign?.id ?? null}
        />
      ))}
    </nav>
  );
}

/** A count and the contracts it counts, each a link to its contract. */
function Named({ contracts, onOpen }: { contracts: ContractView[]; onOpen: (c: ContractView) => void }) {
  return (
    <span className="cmp-named">
      <Count n={contracts.length} />
      {contracts.length ? (
        contracts.map((c) => (
          <button key={c.id} className="link" onClick={() => onOpen(c)} title={c.title}>
            {shortTitle(c.title)}
          </button>
        ))
      ) : (
        <span className="dim">none</span>
      )}
    </span>
  );
}

function ContractGroup({
  snap,
  go,
  contract,
  focused,
  active,
}: TabProps & { contract: ContractView; focused: boolean; active: string | null }) {
  const campaigns = campaignsOf(snap, contract.id);
  const stage = STAGES.find((s) => s.id === contract.stage);
  return (
    <section className="rail-group cmp-group" data-active={focused}>
      <header>
        <button
          className="cmp-contract"
          onClick={() => go({ view: "contracts", id: contract.id })}
          title={`${contract.title}\n${contract.stage}: ${stage?.words ?? ""}\nOpen the contract`}
        >
          <span className="cmp-contract-name">{shortTitle(contract.title)}</span>
          <StageDots stage={contract.stage} />
        </button>
      </header>
      {campaigns.length ? (
        campaigns.map((c) => (
          <CampaignRow
            key={c.id}
            campaign={c}
            active={active === c.id}
            designs={candidatesOf(snap, c.id).map((d) => ({ id: d.id, passed: d.passed }))}
            onOpen={() => go({ id: c.id, focus: null })}
          />
        ))
      ) : (
        <div className="cmp-none" title={whyNone(contract)}>
          no campaign
        </div>
      )}
    </section>
  );
}

/** Why a contract has no campaign, for the hover: it must be frozen first, or none has run. */
function whyNone(contract: ContractView): string {
  if (contract.stage === "frozen") return "Frozen: a campaign may attempt it; none has run";
  if (contract.freeze.ready) return `${contract.stage}: ready to freeze; a campaign needs it frozen`;
  return `${contract.stage}: a campaign needs it frozen, and the validator would refuse that now`;
}

function CampaignRow({
  campaign,
  active,
  designs,
  onOpen,
}: {
  campaign: Campaign;
  active: boolean;
  designs: { id: string; passed: boolean | null }[];
  onOpen: () => void;
}) {
  const stop = campaign.stop ? STOP[campaign.stop] : null;
  return (
    <button className="campaign-row" data-active={active} onClick={onOpen}>
      <span className="campaign-name mono">{campaign.id}</span>
      <span className="dim num">
        <span title={ARM[campaign.arm].words}>{ARM[campaign.arm].label}</span> · {campaign.spent_fe_proofs} of{" "}
        {campaign.budget_fe_proofs} proofs ·{" "}
        <span title={stop ? stop.words : undefined}>
          {stop ? stop.short : campaign.ended ? "ended" : "running"}
        </span>
      </span>
      {designs.length ? (
        <span className="campaign-dots">
          {designs.map((d) => (
            <i
              key={d.id}
              data-status={d.passed === true ? "done" : d.passed === false ? "failed" : "pending"}
              title={d.id}
            />
          ))}
        </span>
      ) : null}
    </button>
  );
}
