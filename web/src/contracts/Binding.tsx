/**
 * Binding, the default page: what binds a design of this contract.
 *
 * Six boxes, one kind of binding each, in the order an engineer reads a requirement: what the
 * housing must carry, what it must keep, what it must meet, how it must be made, what the agent may
 * move, and what is assumed and waits to be confirmed. Two columns when there is room - boxes 1, 3,
 * 5 on the left and 2, 4, 6 on the right, so a long box never leaves a hole beside a short one - and
 * one column, in order, when there is not. Every value is a row that opens in the card.
 */

import { type ReactNode, useMemo } from "react";
import { AUTHORITY, OBJECTIVE, PROCESS, STAGES } from "../app/product";
import { Prov, StageDots } from "../panel/bits";
import type { Authority, ContractView, Layer } from "../records/types";
import {
  DERIVES_THEM,
  LEVEL,
  STRESS,
  STYLE,
  assumptionFocus,
  bearingParts,
  groupsOf,
  judgedUnder,
} from "./model";
import {
  Box,
  EntryGroups,
  EntryRow,
  Line,
  Unloaded,
  VerdictChip,
  clickable,
  useRevealFocus,
  type PageProps,
} from "./parts";

const AUTHORITIES: Authority[] = ["engineer_locked", "agent_bounded", "agent_free"];

function bindingOf(c: ContractView) {
  const layer = (l: Layer) => c.entries.filter((e) => e.layer === l);
  const requirement = layer("requirement");
  const physics = layer("physics");
  const interfaces = layer("interfaces");
  const uses = new Map<string, number>();
  for (const e of c.entries) {
    const id = e.provenance.assumption_id;
    if (id) uses.set(id, (uses.get(id) ?? 0) + 1);
  }
  return {
    // The bearings are what the seats will host, so they sit with the interfaces, not the duty.
    duty: groupsOf([...requirement.filter((e) => e.group !== "bearings"), ...physics], c.items),
    dutyCount: requirement.filter((e) => e.group !== "bearings").length + physics.length,
    physics: physics.length,
    interfaces: groupsOf(interfaces, c.items),
    interfaceCount: interfaces.length,
    bearings: c.items
      .filter((i) => i.kind === "bearing")
      .map((item) => ({
        item,
        ...bearingParts(item),
        designation: c.entries.find((e) => e.path === `${item.path}.designation`) ?? null,
      })),
    limits: groupsOf(layer("limits"), c.items),
    limitCount: layer("limits").length,
    manufacturing: groupsOf(layer("manufacturing"), c.items),
    manufacturingCount: layer("manufacturing").length,
    free: c.entries.filter((e) => e.authority !== "engineer_locked"),
    authority: AUTHORITIES.map((a) => ({ a, n: c.entries.filter((e) => e.authority === a).length })),
    uses,
  };
}

export function Binding({ c, focus, go }: PageProps) {
  const m = useMemo(() => (c.loaded ? bindingOf(c) : null), [c]);
  const scroller = useRevealFocus(focus, c.id);
  if (!c.loaded || !m) return <Unloaded c={c} />;
  const onFocus = (path: string) => go({ id: c.id, focus: path });
  const stage = STAGES.find((s) => s.id === c.stage) ?? STAGES[0];
  // The assumption behind the entry in focus, marked in box 6 so a value leads to its reason.
  const behind = c.entries.find((e) => e.path === focus)?.provenance.assumption_id ?? null;

  const carry = (
    <Box n={1} title="Must carry" sub="the duty" count={m.dutyCount} order={1}>
      <EntryGroups groups={m.duty} focus={focus} onFocus={onFocus} />
      {m.physics === 0 ? (
        <Line blank label="load cases · mesh orders">
          {DERIVES_THEM}
        </Line>
      ) : null}
    </Box>
  );

  const keep = (
    <Box n={2} title="Must keep" sub="the interfaces" count={m.interfaceCount} order={2}>
      {m.interfaceCount ? (
        <EntryGroups groups={m.interfaces} focus={focus} onFocus={onFocus} />
      ) : (
        <Line blank>No interfaces yet: the layout is derived from the requirement by the load tool (GBX-1, not built)</Line>
      )}
      {m.bearings.length ? (
        <>
          <div className="ct-group ct-group-gap">
            {m.interfaceCount ? "the bearings they host" : "the seats to come"}{" "}
            <span className="count">{m.bearings.length}</span>
          </div>
          <table className="ct-mini">
            <tbody>
              {m.bearings.map(({ item, type, seat, designation }) => {
                const path = designation?.path ?? null;
                return (
                  <tr
                    key={item.path}
                    {...(path ? clickable(() => onFocus(path)) : {})}
                    data-focus={path !== null && focus === path}
                    title={`${item.name}: ${item.detail}\n${item.path}`}
                  >
                    <td className="mono ct-mini-key">{item.name}</td>
                    <td>{type}</td>
                    <td className="dim">{seat ? `at ${seat}` : ""}</td>
                    <td className="ct-mini-prov">{designation ? <Prov kind={designation.provenance.kind} /> : null}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </>
      ) : null}
    </Box>
  );

  const meet = (
    <Box n={3} title="Must meet" sub="the verdict" count={m.limitCount} order={3}>
      <EntryGroups groups={m.limits} focus={focus} onFocus={onFocus} />
      <div className="ct-group ct-group-gap">the rule</div>
      <Line label="objective">{OBJECTIVE[c.objective] ?? c.objective}</Line>
      <Line label="stress">{STRESS[c.stress] ?? c.stress}</Line>
      <Line label="verdict rule">
        <span className="mono">{c.verdict_rule_version}</span>
      </Line>
      <button
        className="ct-judged"
        onClick={() => go({ view: "data", page: "axes" })}
        title="The tests this contract implies, on the Data tab's Axes page"
      >
        {judgedUnder(c.scenarios)} <span aria-hidden="true">→</span>
      </button>
    </Box>
  );

  const make = (
    <Box n={4} title="Must be makeable" sub="the process" count={m.manufacturingCount} order={4}>
      <div className="ct-process">
        <b>{PROCESS[c.process] ?? c.process}</b>
        <span className="dim">{c.material}</span>
      </div>
      <EntryGroups groups={m.manufacturing} focus={focus} onFocus={onFocus} />
    </Box>
  );

  const vary = (
    <Box n={5} title="May vary" sub="the agent's authority" count={m.free.length} order={5}>
      <div className="pills ct-box-pad">
        {m.authority.map(({ a, n }) => (
          <span key={a} className="pill" title={AUTHORITY[a].words}>
            {AUTHORITY[a].label} <span className="num">{n}</span>
          </span>
        ))}
      </div>
      {m.free.length ? (
        <div className="ct-rows">
          {m.free.map((e) => (
            <EntryRow
              key={e.path}
              row={{ entry: e, label: e.label }}
              focus={focus}
              onFocus={onFocus}
              extra={
                <>
                  {AUTHORITY[e.authority].label}
                  {e.bounds ? ` · ${e.bounds[0]} to ${e.bounds[1]}` : ""}
                </>
              }
            />
          ))}
        </div>
      ) : (
        <Line>Nothing: every entry is locked. The agent varies only the geometry inside the installation space.</Line>
      )}
    </Box>
  );

  const confirm = (
    <Box n={6} title="To confirm" sub="the assumptions" count={c.assumptions.length} order={6}>
      {c.assumptions.length ? (
        <div className="ct-assumptions">
          {c.assumptions.map((a) => {
            const n = m.uses.get(a.id) ?? 0;
            const target = assumptionFocus(a.id);
            return (
              <button
                key={a.id}
                className="ct-assumption"
                data-focus={focus === target}
                data-related={behind === a.id}
                onClick={() => onFocus(target)}
                title={`Why: ${a.why}`}
              >
                <span className="ct-assumption-id mono">{a.id}</span>
                <span className="ct-assumption-what">{a.what}</span>
                <span className="ct-assumption-tags">
                  {a.varied ? (
                    <span className="pill ct-varied" title="The dataset may vary it to make variants">
                      varied later
                    </span>
                  ) : null}
                  <span className="num dim" title="Entries that take their value from it">
                    {n ? `${n} ${n === 1 ? "entry" : "entries"}` : "no entry"}
                  </span>
                </span>
                <span className="ct-assumption-value">{a.value}</span>
              </button>
            );
          })}
        </div>
      ) : (
        <Line>None: every value is published, a standard's, or the engineer's.</Line>
      )}
    </Box>
  );

  return (
    <div className="stage-scroll ct-page" ref={scroller}>
      <header className="ct-head">
        <h1 className="ct-title">{c.title}</h1>
        <div className="ct-subline">
          <span className="mono">{c.id}</span>
          <span>{c.family}</span>
          <span title={LEVEL[c.level]}>
            {c.level}
            {LEVEL[c.level] ? <span className="dim"> · {LEVEL[c.level]}</span> : null}
          </span>
          <VerdictChip c={c} />
        </div>
        <div className="ct-facts">
          <Fact label="stage" wide>
            <StageDots stage={c.stage} /> <b>{stage.label}</b> <span className="dim">{stage.words}</span>
          </Fact>
          <Fact label="process">{PROCESS[c.process] ?? c.process}</Fact>
          <Fact label="requirement">{STYLE[c.style] ?? c.style}</Fact>
          <Fact label="budget">
            <span className="num">{c.budget_fe_proofs}</span> FE proofs · <span className="num">{c.budget_hours}</span> h
          </Fact>
          <Fact label="priorities">
            {c.priorities.length ? c.priorities.join(" · ") : <span className="dim">none</span>}
          </Fact>
        </div>
      </header>
      <div className="ct-boxes">
        <div className="ct-col">
          {carry}
          {meet}
          {vary}
        </div>
        <div className="ct-col">
          {keep}
          {make}
          {confirm}
        </div>
      </div>
    </div>
  );
}

function Fact({ label, wide = false, children }: { label: string; wide?: boolean; children: ReactNode }) {
  return (
    <div className="ct-fact" data-wide={wide}>
      <div className="ct-fact-label">{label}</div>
      <div className="ct-fact-value">{children}</div>
    </div>
  );
}
