/**
 * A campaign into data: how one campaign's steps become datapoints and tasks (data design §5).
 *
 * Drawn as a diagram, not a list, because the point is the cutting: one strip of steps on the
 * left, and from it a connector to each thing it is cut into - every step a decision record, a
 * decisive step a snapshot task, two steps from one state a preference pair, every design a graded
 * design. What joins from outside the campaign - the task it attempts, the pairs of tasks, the
 * engineer's choice on a design - is set at the side with dashed connectors, so solid and dashed
 * lines tell the two apart in greyscale too.
 *
 * Every count is the record's, 0 today, and the strip's steps carry no example content: a campaign
 * has not run, so there is nothing true to show inside one.
 */

import type { TabProps } from "../app/tab";
import { Blank, Block, Count, Dot } from "../panel/bits";
import { CUT_RULES, CUTS, KINDS, MAKING, type CutId, type KindLetter, type Making } from "../data/kinds";
import type { Snapshot } from "../records/types";
import { stageOf } from "./stages";

export function CampaignPage({ snap, route, go }: TabProps) {
  const focus = route.focus;
  const campaign = stageOf("campaign");
  const campaigns = snap.records.campaigns.length;
  return (
    <>
      <Block title="One campaign, cut into data" aside="every count from the record">
        <div className="flow-diagram-wrap">
          <div className="flow-diagram">
            <KindBox letter="A" title="Task" area="a" snap={snap} focus={focus} go={go} from="outside" />
            <div className="flow-conn" data-from="outside" style={{ gridArea: "ae" }}>
              <span>pairs of tasks, one requirement apart</span>
            </div>
            <KindBox letter="E" title="Counterfactual pair" area="e" snap={snap} focus={focus} go={go} from="outside" />
            <div className="flow-vconn" style={{ gridArea: "down" }}>
              <span>attempted by</span>
            </div>

            <button
              className="flow-strip"
              style={{ gridArea: "camp" }}
              data-focus={focus === "campaign"}
              onClick={() => go({ focus: "campaign" })}
              title={campaign ? `${campaign.label}: ${campaign.what}` : undefined}
            >
              <span className="flow-box-head">
                <span className="flow-box-name">Campaign</span>
                <Count n={campaigns} />
              </span>
              <span className="flow-box-what">one attempt at a frozen task, by one solver, with a budget</span>
              <span className="flow-steps" aria-hidden="true">
                <span>step 1</span>
                <span>step 2</span>
                <span>step 3</span>
                <span className="flow-steps-more">…</span>
                <span>step n</span>
              </span>
              <span className="flow-box-by">
                <Dot status="blank" title="not built" />
                {campaign ? campaign.madeBy(snap) : null}
              </span>
            </button>

            {ROWS.map((row) => (
              <div key={row.area} className="flow-conn" data-from="campaign" style={{ gridArea: `c${row.area}` }}>
                <span>{row.label}</span>
              </div>
            ))}
            <KindBox letter="C" title="Decision record" area="r1" snap={snap} focus={focus} go={go} from="campaign" />
            <CutBox id="snapshots" title="Snapshot task" tag="DAT-2" area="r2" snap={snap} focus={focus} go={go} />
            <CutBox id="preferences" title="Preference pair" area="r3" snap={snap} focus={focus} go={go} />
            <KindBox letter="B" title="Graded design" area="r4" snap={snap} focus={focus} go={go} from="campaign" />

            <div className="flow-conn" data-from="outside" data-dir="left" style={{ gridArea: "db" }} />
            <KindBox letter="D" title="Engineer's choice" area="d" snap={snap} focus={focus} go={go} from="outside" />
          </div>
        </div>
        <div className="flow-key">
          <span>
            <i className="flow-key-line" /> cut from the campaign
          </span>
          <span>
            <i className="flow-key-line" data-from="outside" /> joins from outside it
          </span>
          <span>
            <Dot status="pending" /> built, none yet
          </span>
          <span>
            <Dot status="blank" /> not built
          </span>
        </div>
      </Block>

      <Block title="The rules of the cut" count={CUT_RULES.length}>
        <div className="pills">
          {CUT_RULES.map((rule) => (
            <span key={rule.label} className="pill" title={rule.words}>
              {rule.label}
            </span>
          ))}
        </div>
      </Block>

      <Blank
        title="Nothing to cut yet"
        waits="No campaign has run: the agent (AGT) and the record (DAT-1) are not built"
      />
    </>
  );
}

const cutFrom = (id: CutId) => CUTS.find((c) => c.id === id)?.from ?? "";

/** The four things cut from the campaign, a row each, with the connector's words. */
const ROWS: { area: string; label: string }[] = [
  { area: "r1", label: cutFrom("decisions") },
  { area: "r2", label: cutFrom("snapshots") },
  { area: "r3", label: cutFrom("preferences") },
  { area: "r4", label: "every design, with its evaluations" },
];

const KIND_WHAT: Record<KindLetter, string> = {
  A: "the frozen contract: the question",
  B: "every design with its evaluations, failures included",
  C: "every step: what was seen, decided and why, what happened",
  D: "accept or reject a graded design, with the reason",
  E: "two contracts one requirement apart, and how the design changed",
};

function KindBox({
  letter,
  title,
  area,
  snap,
  focus,
  go,
  from,
}: {
  letter: KindLetter;
  title: string;
  area: string;
  snap: Snapshot;
  focus: string | null;
  go: TabProps["go"];
  from: "campaign" | "outside";
}) {
  const kind = KINDS.find((k) => k.letter === letter);
  if (!kind) return <span />;
  const id = `kind:${letter}`;
  return (
    <Box
      area={area}
      from={from}
      badge={letter}
      title={title}
      n={kind.count(snap)}
      what={KIND_WHAT[letter]}
      learning={kind.learning}
      madeBy={kind.madeBy}
      making={kind.making}
      hover={`${letter}. ${kind.name}: ${kind.what}`}
      focused={focus === id}
      onFocus={() => go({ focus: id })}
    />
  );
}

function CutBox({
  id,
  title,
  tag,
  area,
  snap,
  focus,
  go,
}: {
  id: CutId;
  title: string;
  tag?: string;
  area: string;
  snap: Snapshot;
  focus: string | null;
  go: TabProps["go"];
}) {
  const cut = CUTS.find((c) => c.id === id);
  if (!cut) return <span />;
  const key = `cut:${id}`;
  return (
    <Box
      area={area}
      from="campaign"
      tag={tag}
      title={title}
      n={cut.count(snap)}
      what={cut.what}
      learning={cut.learning}
      madeBy={cut.madeBy}
      making={cut.making}
      hover={cut.words}
      focused={focus === key}
      onFocus={() => go({ focus: key })}
    />
  );
}

function Box(props: {
  area: string;
  from: "campaign" | "outside";
  badge?: string;
  tag?: string;
  title: string;
  n: number;
  what: string;
  learning: string;
  madeBy: string;
  making: Making;
  hover: string;
  focused: boolean;
  onFocus: () => void;
}) {
  return (
    <button
      className="flow-box"
      style={{ gridArea: props.area }}
      data-from={props.from}
      data-focus={props.focused}
      onClick={props.onFocus}
      title={props.hover}
    >
      <span className="flow-box-head">
        {props.badge ? <span className="flow-badge">{props.badge}</span> : null}
        <span className="flow-box-name">{props.title}</span>
        {props.tag ? <span className="flow-box-tag">{props.tag}</span> : null}
        <Count n={props.n} />
      </span>
      <span className="flow-box-what">{props.what}</span>
      <span className="flow-box-kv">
        <span className="dim">trains</span>
        <span>{props.learning}</span>
        <span className="dim">made by</span>
        <span>
          <Dot status={props.making === "built" ? "pending" : "blank"} title={MAKING[props.making]} /> {props.madeBy}
        </span>
      </span>
    </button>
  );
}
