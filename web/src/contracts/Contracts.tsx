/**
 * The Contract tab: one page, one contract (the engineer, 8 Oct 19:52). No rail and no card, so the
 * page has the full width, as a product's form does. The views of 8 October, a page per layer with
 * an entry card, are archived in `archive/web/contracts-v1/`.
 */

import type { Tab, TabProps } from "../app/tab";
import { ContractPage } from "./ContractPage";

function Stage({ snap }: TabProps) {
  const contract = snap.contracts[0];
  if (!contract) {
    return (
      <div className="stage-scroll">
        <div className="later">
          <h2>No contract yet</h2>
        </div>
      </div>
    );
  }
  return <ContractPage contract={contract} snap={snap} />;
}

// The bar names the contract on every tab (App's default), so this tab needs no context of its own.
export const contractsTab: Tab = { Stage, cardName: "" };
