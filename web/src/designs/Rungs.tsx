/**
 * The rungs: the label ladder of plan §7.2 - what each rung needs and who signs it. Qualification
 * attaches to a process and a part plan, not to a geometry, so a design carries the highest rung it
 * has reached and never a bare "verified".
 *
 * A rule runs under the second rung: above it the platform stands alone, below it partners sign.
 */

import { RungPill } from "./bits";
import { RUNG, RUNG_ORDER } from "./words";

export function Rungs() {
  return (
    <>
      <div className="tbl-wrap dsg-rungs">
        <table className="tbl">
          <thead>
            <tr>
              <th className="num">#</th>
              <th>Rung</th>
              <th>What it needs</th>
              <th>Who signs</th>
            </tr>
          </thead>
          <tbody>
            {RUNG_ORDER.map((r, i) => (
              <tr key={r} data-own={RUNG[r].own}>
                <td className="num">{i + 1}</td>
                <td>
                  <RungPill rung={r} />
                </td>
                <td>{RUNG[r].needs}</td>
                <td className={RUNG[r].own ? undefined : "dim"}>{RUNG[r].signs}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="dsg-line">The platform reaches the second rung on its own; the rest need partners</p>
    </>
  );
}
