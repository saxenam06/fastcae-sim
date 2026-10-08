/**
 * The head every Campaigns page opens with: the campaign in view - the contract it attempts, who
 * attempts it, the model and the brief, the budget spent of the total, how it stopped. Before any
 * campaign it says so, with what one needs: a frozen contract, counted from the snapshot.
 *
 * One head for all four pages, so moving between them never changes what you are looking at.
 */

import { shortTitle } from "../app/product";
import type { TabProps } from "../app/tab";
import { Count, StageDots } from "../panel/bits";
import { frozen, inView, readyToFreeze } from "./records";
import { ARM, STOP } from "./words";

export function CampaignHead({ snap, route, go }: TabProps) {
  const { campaign, contract } = inView(snap, route);
  const contractLink = contract ? (
    <button
      className="link"
      onClick={() => go({ view: "contracts", id: contract.id })}
      title={`${contract.title} - open the contract`}
    >
      {shortTitle(contract.title)}
    </button>
  ) : null;

  if (!campaign) {
    const any = snap.records.campaigns.length > 0;
    return (
      <header className="page-head">
        <h1>{any ? "No campaign in view" : "No campaign yet"}</h1>
        {contract ? (
          <>
            {contractLink}
            <StageDots stage={contract.stage} />
          </>
        ) : null}
        <span className="dim">
          {any ? "pick one on the left · " : ""}a campaign attempts a frozen contract ·{" "}
          <Count n={frozen(snap).length} /> frozen · <Count n={readyToFreeze(snap).length} /> ready to freeze
        </span>
      </header>
    );
  }

  const stop = campaign.stop ? STOP[campaign.stop] : null;
  return (
    <header className="page-head">
      <h1 className="mono">{campaign.id}</h1>
      {contractLink ?? <span className="mono dim">{campaign.contract}</span>}
      <span className="pill" title={ARM[campaign.arm].words}>
        {ARM[campaign.arm].label}
      </span>
      {campaign.model ? (
        <span className="dim">
          model <span className="mono">{campaign.model}</span>
        </span>
      ) : null}
      {campaign.brief_version ? (
        <span className="dim">
          brief <span className="mono">{campaign.brief_version}</span>
        </span>
      ) : null}
      <span className="dim">
        <span className="num">{campaign.spent_fe_proofs}</span> of{" "}
        <span className="num">{campaign.budget_fe_proofs}</span> FE proofs
      </span>
      <span
        className="pill cmp-pill"
        data-on={stop !== null}
        title={stop ? [stop.words, campaign.stop_reason].filter(Boolean).join("\n") : undefined}
      >
        {stop ? `stopped: ${stop.short}` : campaign.ended ? "ended" : "running"}
      </span>
    </header>
  );
}
