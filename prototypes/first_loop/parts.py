"""PROTOTYPE (LOP-26) - production's parts as the optimiser's design (the engineer, 12 October 10:31-11:16: "make
optimization only build features with those primitive in the library", where they go the optimiser's: Refine;
docs/features/loop/2026-10-12-primitive-library.md).

Two shapes carry every family, in the height field's plan (each column one height off its base: an end wall, or
the split beside a side wall):
- a **member**: a straight plate between two nodes, `width` mm wide (its family's), its height from `h` at node a
  to `h` at node b, linear along it (mm off each column's base). Spokes, links, ties, rims, grids, fins, belts,
  gussets and arms are members;
- a **ring** round a fixed axis, one height `h`: an "annulus" from a fixed `r_in` (a bore's) out to its radius `r` (a
  bearing's boss, a tower round a seat's tube, a seal's boss round a shaft's exit), "solid" from the axis out to `r`,
  or a "band" `width` wide about `r` (a ring rib).
A node is "fixed" (a bolt, a mount), slides round a "circle" (a boss's rim: its angle) or along an "edge" (the
half's outline: its arc length), or is "free" (a junction: x and y, within `reach` mm of its start).

A part covers the columns of its half within its footprint, its edge soft (`EDGE` mm, tanh), so a moving part
changes the columns smoothly; a column's height is the tallest part over it (a smooth maximum, the p-norm at `Q`:
never the sum, so a node is no hot spot); a column no part covers holds nothing. The design variables, each in
[0, 1], are every node's free coordinates and every part's sizes within their ranges. `PartsMap.heights(x)` gives
each column's height (mm), `PartsMap.jacobian(x)` its derivatives (mm a unit of x), both cached by x;
`topo.Voxels` takes them in height mode when `model["parts"]` is given (`topo_free.py --parts <file>`).

The parts file (`<label>.json`, written by `refine_read.py`), in mm and radians:
{"edges": {name: [[x, y], ...] closed}, "nodes": [{"kind", "half", "xy" | "centre", "r", "angle", "range" |
 "edge", "s", "range" | "xy0", "reach"}], "members": [{"family", "half", "a", "b", "width", "h": [h_a, h_b],
 "h_range": [lo, hi]}], "rings": [{"family", "half", "kind": "solid" | "band", "centre", "r", "r_range", "width",
 "h", "h_range"}]}

    parts.py --check      the derivatives against central differences on a synthetic layout
"""

import math
import sys

import numpy as np
import scipy.sparse as sp
from scipy.spatial import cKDTree

EDGE = 1.5  # mm: the footprint's soft edge (tanh's scale)
Q = 8.0  # the smooth maximum's exponent: two equal parts at a node stand 9 % taller than one
LAYER = {"motor_side": 1, "cover": 10_001}  # each half's first run of columns, from the split or its wall (`topo.height_columns`)
REACH_PAD = 4.0  # a part's columns are looked for this many edges past its footprint
# 1/mm: the least height a part holds, a smooth step on the part's own height (12 October 12:55: on the columns, as the
# free run has it, the least height took away a part's edge columns, which its soft edge gives part of its height, and
# left the model's parts narrower and softer than the plates drawn: `rg20_parts` 1.42 × the tilt's line in FE)
GATE = 1.0


def _node_count(node: dict) -> int:
    return {"fixed": 0, "circle": 1, "edge": 1, "free": 2}[node["kind"]]


def uneven_capsule(p: np.ndarray, a: np.ndarray, b: np.ndarray, ra: float, rb: float) -> np.ndarray:
    """The signed distance (mm, < 0 inside) from plan points p (n, 2) to the hull of two discs (a, ra) and (b, rb)
    (Quilez's uneven capsule): a web between two bosses."""
    ba = b - a
    length = max(float(np.hypot(*ba)), 1e-9)
    e = ba / length
    q = p - a[None, :]
    y = q @ e
    xx = np.abs(q @ np.array([-e[1], e[0]]))
    if abs(ra - rb) >= length:  # one disc within the other
        return np.minimum(np.hypot(*q.T) - ra, np.hypot(*(p - b[None, :]).T) - rb)
    s = (ra - rb) / length
    c = math.sqrt(1.0 - s * s)
    k = -s * xx + c * y
    return np.where(k < 0.0, np.hypot(xx, y) - ra, np.where(k > c * length, np.hypot(xx, y - length) - rb, c * xx + s * y - ra))


class PartsMap:
    """The parts' map onto the height field's columns (see the module's text)."""

    def __init__(self, spec: dict, centres: np.ndarray, layer: np.ndarray):
        self.spec = spec
        self.nodes = spec["nodes"]
        self.members = spec.get("members", [])
        self.rings = spec.get("rings", [])
        self.centres = np.asarray(centres, float)
        self.n_cols = len(self.centres)
        idx = 0
        self.node_var = []
        shared = {}  # a wheel's spokes turn together, a grid's nodes move with its frame: one set of variables each
        for nd in self.nodes:
            if nd["kind"] in ("spoke", "lattice"):
                key = (nd["kind"], nd["share"] if nd["kind"] == "spoke" else nd["grid"])
                if key not in shared:
                    k = 1 if nd["kind"] == "spoke" else 4
                    shared[key] = list(range(idx, idx + k))
                    idx += k
                self.node_var.append(shared[key])
                continue
            k = _node_count(nd)
            self.node_var.append(list(range(idx, idx + k)))
            idx += k
        self.grids = spec.get("grids") or {}
        self.member_var = []
        for _ in self.members:
            self.member_var.append([idx, idx + 1])
            idx += 2
        self.ring_var = []
        for _ in self.rings:
            self.ring_var.append([idx, idx + 1])  # its radius, its height
            idx += 2
        self.n_vars = idx
        layer = np.asarray(layer)
        self.trees = {}
        for half, lay in LAYER.items():
            sel = np.flatnonzero(layer == lay)
            if len(sel):
                self.trees[half] = (sel, cKDTree(self.centres[sel]))
        self.edges = {}
        for name, pts in (spec.get("edges") or {}).items():
            p = np.asarray(pts, float)
            if np.hypot(*(p[0] - p[-1])) > 1e-9:
                p = np.vstack([p, p[:1]])  # closed
            seg = np.diff(p, axis=0)
            length = np.hypot(seg[:, 0], seg[:, 1])
            self.edges[name] = (p, np.concatenate([[0.0], np.cumsum(length)]), seg, length)
        self.least = float(spec.get("least_mm") or 0.0)  # a part lower than this holds nothing (no paint)
        self._key, self._h, self._j = None, None, None

    def _gated(self, hgt: np.ndarray):
        """A part's height through the least height's smooth step on it, and the slope (d gated / d height)."""
        if self.least <= 0.0:
            return hgt, np.ones_like(hgt)
        t = np.tanh(GATE * (hgt - self.least))
        g = 0.5 * (1.0 + t)
        return hgt * g, g + hgt * 0.5 * GATE * (1.0 - t * t)

    # --- the design variables -------------------------------------------------------------------------------------
    def start(self) -> np.ndarray:
        """The start: every node where the reading put it (each sliding or free coordinate at its range's middle unless
        the node says where), every part at its read size."""
        x = np.full(self.n_vars, 0.5)
        for nd, v in zip(self.nodes, self.node_var, strict=True):
            if nd["kind"] == "circle":
                lo, hi = nd["range"]
                x[v[0]] = (nd["angle"] - lo) / (hi - lo)
            elif nd["kind"] == "edge":
                lo, hi = nd["range"]
                x[v[0]] = (nd["s"] - lo) / (hi - lo)
        for m, v in zip(self.members, self.member_var, strict=True):
            lo, hi = m["h_range"]
            x[v] = (np.asarray(m["h"], float) - lo) / (hi - lo)
        for r, v in zip(self.rings, self.ring_var, strict=True):
            lo, hi = r["hole_range"] if r["kind"] == "web" else r["r_range"]
            x[v[0]] = ((r["hole"] if r["kind"] == "web" else r["r"]) - lo) / (hi - lo) if hi > lo else 0.5
            lo, hi = r["h_range"]
            x[v[1]] = (r["h"] - lo) / (hi - lo)
        return np.clip(x, 0.0, 1.0)

    def _along(self, name: str, s: float):
        """The point at arc length s (mm, wrapping) along a closed edge, and its unit tangent."""
        p, cum, seg, length = self.edges[name]
        s = s % cum[-1]
        i = int(np.clip(np.searchsorted(cum, s, side="right") - 1, 0, len(seg) - 1))
        t = (s - cum[i]) / max(length[i], 1e-12)
        return p[i] + t * seg[i], seg[i] / max(length[i], 1e-12)

    def nodes_at(self, x: np.ndarray):
        """Each node's position (mm) and its derivatives: per node, a list of (variable, dP/dx (2,))."""
        pos = np.zeros((len(self.nodes), 2))
        d_pos = [[] for _ in self.nodes]
        for i, (nd, v) in enumerate(zip(self.nodes, self.node_var, strict=True)):
            kind = nd["kind"]
            if kind == "fixed":
                pos[i] = nd["xy"]
            elif kind == "circle":
                lo, hi = nd["range"]
                th = lo + (hi - lo) * x[v[0]]
                c, r = np.asarray(nd["centre"], float), float(nd["r"])
                pos[i] = c + r * np.array([math.cos(th), math.sin(th)])
                d_pos[i].append((v[0], r * (hi - lo) * np.array([-math.sin(th), math.cos(th)])))
            elif kind == "edge":
                lo, hi = nd["range"]
                p, tangent = self._along(nd["edge"], lo + (hi - lo) * x[v[0]])
                pos[i] = p
                d_pos[i].append((v[0], (hi - lo) * tangent))
            elif kind == "spoke":  # on a circle at its own angle, the wheel's turn added (shared)
                turn = float(nd["turn"])
                th = float(nd["angle"]) + turn * (2.0 * x[v[0]] - 1.0)
                c, r = np.asarray(nd["centre"], float), float(nd["r"])
                pos[i] = c + r * np.array([math.cos(th), math.sin(th)])
                d_pos[i].append((v[0], 2.0 * turn * r * np.array([-math.sin(th), math.cos(th)])))
            elif kind == "lattice":  # a triangular grid's node (i, j): its frame shifted, turned and stretched (shared)
                g = self.grids[nd["grid"]]
                u0, p0 = float(g["angle"]), float(g["pitch"])
                e1 = np.array([math.cos(u0), math.sin(u0)])
                e2 = np.array([math.cos(u0 + math.pi / 3.0), math.sin(u0 + math.pi / 3.0)])
                local = float(nd["i"]) * e1 + float(nd["j"]) * e2
                shift, turn, stretch = float(g["shift"]), float(g["turn"]), float(g["stretch"])
                rot = turn * (2.0 * x[v[2]] - 1.0)
                pitch = p0 * (1.0 + stretch * (2.0 * x[v[3]] - 1.0))
                cr, sr = math.cos(rot), math.sin(rot)
                rl = np.array([cr * local[0] - sr * local[1], sr * local[0] + cr * local[1]])
                pos[i] = np.asarray(g["origin"], float) + shift * (2.0 * x[v[:2]] - 1.0) + pitch * rl
                d_pos[i].append((v[0], np.array([2.0 * shift, 0.0])))
                d_pos[i].append((v[1], np.array([0.0, 2.0 * shift])))
                d_pos[i].append((v[2], 2.0 * turn * pitch * np.array([-sr * local[0] - cr * local[1], cr * local[0] - sr * local[1]])))
                d_pos[i].append((v[3], 2.0 * stretch * p0 * rl))
            else:
                reach = float(nd["reach"])
                pos[i] = np.asarray(nd["xy0"], float) + reach * (2.0 * x[v] - 1.0)
                d_pos[i].append((v[0], np.array([2.0 * reach, 0.0])))
                d_pos[i].append((v[1], np.array([0.0, 2.0 * reach])))
        return pos, d_pos

    def params(self, x: np.ndarray) -> dict:
        """The parts at x in mm: every node's place, every member's ends and heights, every ring's radius and height."""
        pos, _ = self.nodes_at(x)
        members = []
        for m, v in zip(self.members, self.member_var, strict=True):
            lo, hi = m["h_range"]
            members.append(dict(m, h=[float(lo + (hi - lo) * x[v[0]]), float(lo + (hi - lo) * x[v[1]])],
                                ends=[pos[m["a"]].tolist(), pos[m["b"]].tolist()]))  # fmt: skip
        rings = []
        for r, v in zip(self.rings, self.ring_var, strict=True):
            lo_h, hi_h = r["h_range"]
            if r["kind"] == "web":
                lo, hi = r["hole_range"]
                rings.append(dict(r, hole=float(lo + (hi - lo) * x[v[0]]), h=float(lo_h + (hi_h - lo_h) * x[v[1]])))
                continue
            lo, hi = r["r_range"]
            rings.append(dict(r, r=float(lo + (hi - lo) * x[v[0]]), h=float(lo_h + (hi_h - lo_h) * x[v[1]])))
        nodes = [dict(nd, at=pos[i].tolist()) for i, nd in enumerate(self.nodes)]
        return dict(self.spec, nodes=nodes, members=members, rings=rings)

    # --- the map --------------------------------------------------------------------------------------------------
    def _evaluate(self, x: np.ndarray) -> None:
        x = np.asarray(x, float)
        key = x.tobytes()
        if key == self._key:
            return
        pos, d_pos = self.nodes_at(x)
        pair_cols, pair_vals = [], []  # each part's covered columns and its height over them (mm)
        rows_d, vars_d, data_d, offs = [], [], [], []  # each derivative: its pairs' offset, the variable, dv/dx
        n_pairs = 0
        for m, v in zip(self.members, self.member_var, strict=True):
            if m["half"] not in self.trees:
                continue
            sel, tree = self.trees[m["half"]]
            a, b = pos[m["a"]], pos[m["b"]]
            u = b - a
            l2 = max(float(u @ u), 1e-9)
            width = float(m["width"])
            radius = 0.5 * math.sqrt(l2) + 0.5 * width + REACH_PAD * EDGE
            idx = tree.query_ball_point(0.5 * (a + b), radius)
            if not idx:
                continue
            cols = sel[np.asarray(idx, np.int64)]
            c = self.centres[cols]
            w = c - a[None, :]
            s_raw = (w @ u) / l2
            s = np.clip(s_raw, 0.0, 1.0)
            inner = (s_raw > 0.0) & (s_raw < 1.0)
            dvec = c - (a[None, :] + s[:, None] * u[None, :])
            d = np.maximum(np.hypot(dvec[:, 0], dvec[:, 1]), 1e-9)
            nrm = dvec / d[:, None]
            th = np.tanh((0.5 * width - d) / EDGE)
            f = 0.5 * (1.0 + th)
            f_d = -0.5 * (1.0 - th * th) / EDGE
            lo, hi = m["h_range"]
            ha, hb = lo + (hi - lo) * x[v[0]], lo + (hi - lo) * x[v[1]]
            height, slope = self._gated(ha + (hb - ha) * s)
            val = f * height
            keep = val > 1e-12
            if not keep.any():
                continue
            cols, c, w, s, inner, nrm, f, f_d, height, slope, val = (q[keep] for q in (cols, c, w, s, inner, nrm, f, f_d, height, slope, val))
            k = len(cols)
            pair_cols.append(cols)
            pair_vals.append(val)
            # the heights
            for var, dv in ((v[0], f * slope * (1.0 - s) * (hi - lo)), (v[1], f * slope * s * (hi - lo))):
                offs.append(n_pairs)
                vars_d.append(var)
                data_d.append(dv)
            # the ends: the distance by the envelope theorem, the place along it where it is inside
            ds_a = np.where(inner[:, None], (-u[None, :] - w + 2.0 * s[:, None] * u[None, :]) / l2, 0.0)
            ds_b = np.where(inner[:, None], (w - 2.0 * s[:, None] * u[None, :]) / l2, 0.0)
            dv_a = (f_d * height)[:, None] * (-nrm * (1.0 - s)[:, None]) + (f * slope * (hb - ha))[:, None] * ds_a
            dv_b = (f_d * height)[:, None] * (-nrm * s[:, None]) + (f * slope * (hb - ha))[:, None] * ds_b
            for node, dv_end in ((m["a"], dv_a), (m["b"], dv_b)):
                for var, dp in d_pos[node]:
                    offs.append(n_pairs)
                    vars_d.append(var)
                    data_d.append(dv_end @ dp)
            rows_d.extend([k] * (2 + sum(len(d_pos[nd_]) for nd_ in (m["a"], m["b"]))))
            n_pairs += k
        for r, v in zip(self.rings, self.ring_var, strict=True):
            if r["half"] not in self.trees:
                continue
            sel, tree = self.trees[r["half"]]
            centre = np.asarray(r["centre"], float)
            lo_h, hi_h = r["h_range"]
            height, slope = self._gated(np.asarray(lo_h + (hi_h - lo_h) * x[v[1]], float))
            width = float(r.get("width") or 0.0)
            if r["kind"] == "web":  # a plate over the hull of two bosses' discs, a round hole in it: v[0] the hole's radius
                lo, hi = r["hole_range"]
                hole = lo + (hi - lo) * x[v[0]]
                c2 = np.asarray(r["centre2"], float)
                r1, r2 = float(r["r1"]), float(r["r2"])
                idx = tree.query_ball_point(0.5 * (centre + c2), 0.5 * float(np.hypot(*(c2 - centre))) + max(r1, r2) + REACH_PAD * EDGE)
                if not idx:
                    continue
                cols = sel[np.asarray(idx, np.int64)]
                f_cap = 0.5 * (1.0 + np.tanh(-uneven_capsule(self.centres[cols], centre, c2, r1, r2) / EDGE))
                rho_h = np.hypot(*(self.centres[cols] - np.asarray(r["hole_at"], float)[None, :]).T)
                th_h = np.tanh((hole - rho_h) / EDGE)
                f = f_cap * (0.5 - 0.5 * th_h)
                df_dr = -f_cap * 0.5 * (1.0 - th_h * th_h) / EDGE
            elif r["kind"] == "arc":  # a rib along a circle's arc from a0 to a1 (radians, counter-clockwise), `width` wide: v[0] its radius
                lo, hi = r["r_range"]
                rad = lo + (hi - lo) * x[v[0]]
                idx = tree.query_ball_point(centre, rad + 0.5 * width + REACH_PAD * EDGE)
                if not idx:
                    continue
                cols = sel[np.asarray(idx, np.int64)]
                rel = self.centres[cols] - centre[None, :]
                rho = np.hypot(*rel.T)
                a0, a1 = float(r["a0"]), float(r["a1"])
                within = np.mod(np.arctan2(rel[:, 1], rel[:, 0]) - a0, 2.0 * math.pi) <= np.mod(a1 - a0, 2.0 * math.pi)
                ends = []
                for a_ in (a0, a1):  # past its span, the distance to the nearer end
                    dr_ = np.array([math.cos(a_), math.sin(a_)])
                    to = self.centres[cols] - (centre + rad * dr_)[None, :]
                    d_e = np.maximum(np.hypot(*to.T), 1e-9)
                    ends.append((d_e, -(to @ dr_) / d_e))
                near0 = ends[0][0] <= ends[1][0]
                d = np.where(within, np.abs(rho - rad), np.where(near0, ends[0][0], ends[1][0]))
                dd = np.where(within, -np.sign(rho - rad), np.where(near0, ends[0][1], ends[1][1]))
                th = np.tanh((0.5 * width - d) / EDGE)
                f = 0.5 * (1.0 + th)
                df_dr = -0.5 * (1.0 - th * th) * dd / EDGE
            else:
                lo, hi = r["r_range"]
                rad = lo + (hi - lo) * x[v[0]]
                reach = rad + (0.5 * width if r["kind"] == "band" else 0.0) + REACH_PAD * EDGE
                idx = tree.query_ball_point(centre, reach)
                if not idx:
                    continue
                cols = sel[np.asarray(idx, np.int64)]
                rho = np.hypot(*(self.centres[cols] - centre[None, :]).T)
                if r["kind"] == "band":
                    th = np.tanh((0.5 * width - np.abs(rho - rad)) / EDGE)
                    df_dr = 0.5 * (1.0 - th * th) * np.sign(rho - rad) / EDGE
                    f = 0.5 * (1.0 + th)
                elif r["kind"] == "annulus":  # from its fixed inner radius (a bore's) out to r
                    th = np.tanh((rad - rho) / EDGE)
                    inner = 0.5 * (1.0 + np.tanh((rho - float(r["r_in"])) / EDGE))
                    df_dr = 0.5 * (1.0 - th * th) / EDGE * inner
                    f = 0.5 * (1.0 + th) * inner
                else:
                    th = np.tanh((rad - rho) / EDGE)
                    df_dr = 0.5 * (1.0 - th * th) / EDGE
                    f = 0.5 * (1.0 + th)
            val = f * height
            keep = val > 1e-12
            if not keep.any():
                continue
            cols, f, df_dr, val = cols[keep], f[keep], df_dr[keep], val[keep]
            k = len(cols)
            pair_cols.append(cols)
            pair_vals.append(val)
            for var, dv in ((v[0], df_dr * height * (hi - lo)), (v[1], f * slope * (hi_h - lo_h))):
                offs.append(n_pairs)
                vars_d.append(var)
                data_d.append(dv)
            rows_d.extend([k, k])
            n_pairs += k
        hgt = np.zeros(self.n_cols)
        if n_pairs:
            cols_all = np.concatenate(pair_cols)
            vals_all = np.concatenate(pair_vals)
            total = np.zeros(self.n_cols)
            np.add.at(total, cols_all, vals_all**Q)
            covered = total > 0.0
            hgt[covered] = total[covered] ** (1.0 / Q)
            weight = (vals_all / np.maximum(hgt[cols_all], 1e-300)) ** (Q - 1.0)  # d(height) / d(a part's value)
            jr, jc, jv = [], [], []
            for off, var, dv, k in zip(offs, vars_d, data_d, rows_d, strict=True):
                jr.append(cols_all[off : off + k])
                jc.append(np.full(k, var, np.int64))
                jv.append(weight[off : off + k] * dv)
            jac = sp.csr_matrix((np.concatenate(jv), (np.concatenate(jr), np.concatenate(jc))), shape=(self.n_cols, self.n_vars))
        else:
            jac = sp.csr_matrix((self.n_cols, self.n_vars))
        self._key, self._h, self._j = key, hgt, jac

    def heights(self, x: np.ndarray) -> np.ndarray:
        """Each column's height (mm) at x."""
        self._evaluate(x)
        return self._h

    def jacobian(self, x: np.ndarray):
        """d(each column's height, mm) / d(each design variable), sparse (columns, variables)."""
        self._evaluate(x)
        return self._j


def _check() -> None:
    """The derivatives against central differences on a synthetic layout (every node kind, members, both rings)."""
    rng = np.random.default_rng(7)
    g = np.arange(-60.0, 60.01, 4.0)
    gx, gy = np.meshgrid(g, g, indexing="ij")
    centres = np.column_stack([gx.ravel(), gy.ravel()])
    layer = np.ones(len(centres), int)
    square = [[-50.0, -50.0], [50.0, -50.0], [50.0, 50.0], [-50.0, 50.0]]
    spec = {
        "least_mm": 8.0,
        "edges": {"outline": square},
        "nodes": [
            {"kind": "fixed", "half": "motor_side", "xy": [-30.0, 20.0]},
            {"kind": "circle", "half": "motor_side", "centre": [0.0, 0.0], "r": 18.0, "angle": 0.3, "range": [-0.2, 0.9]},
            {"kind": "edge", "half": "motor_side", "edge": "outline", "s": 60.0, "range": [40.0, 80.0]},
            {"kind": "free", "half": "motor_side", "xy0": [10.0, -25.0], "reach": 15.0},
            {"kind": "circle", "half": "motor_side", "centre": [0.0, 0.0], "r": 18.0, "angle": 2.4, "range": [2.0, 2.9]},
            {"kind": "spoke", "half": "motor_side", "centre": [0.0, 0.0], "r": 18.0, "angle": 4.0, "turn": 0.3, "share": "w1"},  # 5
            {"kind": "spoke", "half": "motor_side", "centre": [0.0, 0.0], "r": 44.0, "angle": 4.0, "turn": 0.3, "share": "w1"},
            {"kind": "spoke", "half": "motor_side", "centre": [0.0, 0.0], "r": 18.0, "angle": 5.2, "turn": 0.3, "share": "w1"},
            {"kind": "spoke", "half": "motor_side", "centre": [0.0, 0.0], "r": 44.0, "angle": 5.2, "turn": 0.3, "share": "w1"},
            {"kind": "lattice", "half": "motor_side", "grid": "g1", "i": 0, "j": 0},  # 9
            {"kind": "lattice", "half": "motor_side", "grid": "g1", "i": 1, "j": 0},
            {"kind": "lattice", "half": "motor_side", "grid": "g1", "i": 0, "j": 1},
        ],
        "grids": {"g1": {"origin": [20.0, 25.0], "angle": 0.4, "pitch": 18.0, "shift": 6.0, "turn": 0.2, "stretch": 0.2}},
        "members": [
            {"family": "tie", "half": "motor_side", "a": 1, "b": 0, "width": 8.0, "h": [16.0, 11.0], "h_range": [0.0, 24.0]},
            {"family": "spoke", "half": "motor_side", "a": 1, "b": 2, "width": 8.0, "h": [20.0, 9.0], "h_range": [0.0, 24.0]},
            {"family": "link", "half": "motor_side", "a": 3, "b": 2, "width": 8.0, "h": [12.0, 18.0], "h_range": [0.0, 24.0]},
            {"family": "spoke", "half": "motor_side", "a": 4, "b": 3, "width": 8.0, "h": [14.0, 14.0], "h_range": [0.0, 24.0]},
            {"family": "spoke", "half": "motor_side", "a": 5, "b": 6, "width": 8.0, "h": [18.0, 12.0], "h_range": [0.0, 24.0]},
            {"family": "spoke", "half": "motor_side", "a": 7, "b": 8, "width": 8.0, "h": [17.0, 13.0], "h_range": [0.0, 24.0]},
            {"family": "grid", "half": "motor_side", "a": 9, "b": 10, "width": 8.0, "h": [15.0, 15.0], "h_range": [0.0, 24.0]},
            {"family": "grid", "half": "motor_side", "a": 10, "b": 11, "width": 8.0, "h": [14.0, 16.0], "h_range": [0.0, 24.0]},
            {"family": "grid", "half": "motor_side", "a": 11, "b": 9, "width": 8.0, "h": [13.0, 15.0], "h_range": [0.0, 24.0]},
        ],
        "rings": [
            {"family": "boss", "half": "motor_side", "kind": "solid", "centre": [0.0, 0.0], "r": 16.0, "r_range": [10.0, 24.0], "h": 15.0, "h_range": [0.0, 24.0]},
            {"family": "ring rib", "half": "motor_side", "kind": "band", "centre": [0.0, 0.0], "r": 34.0, "r_range": [28.0, 40.0], "width": 8.0,
             "h": 12.0, "h_range": [0.0, 24.0]},
            {"family": "boss", "half": "motor_side", "kind": "annulus", "centre": [-30.0, -30.0], "r_in": 9.0, "r": 17.0, "r_range": [12.0, 24.0],
             "h": 13.0, "h_range": [0.0, 24.0]},
            {"family": "web", "half": "motor_side", "kind": "web", "centre": [-40.0, 35.0], "centre2": [-5.0, 45.0], "r1": 12.0, "r2": 9.0,
             "hole_at": [-22.0, 40.0], "hole": 5.0, "hole_range": [0.0, 9.0], "h": 11.0, "h_range": [0.0, 24.0]},
            {"family": "arc", "half": "motor_side", "kind": "arc", "centre": [10.0, -10.0], "r": 38.0, "r_range": [32.0, 44.0], "width": 8.0,
             "a0": 3.6, "a1": 5.3, "h": 14.0, "h_range": [0.0, 24.0]},
        ],
    }  # fmt: skip
    pm = PartsMap(spec, centres, layer)
    x = np.clip(pm.start() + rng.uniform(-0.15, 0.15, pm.n_vars), 0.05, 0.95)
    weights = rng.normal(size=pm.n_cols)
    grad = pm.jacobian(x).T @ weights
    step, worst = 1e-6, 0.0
    for k in range(pm.n_vars):
        e = np.zeros(pm.n_vars)
        e[k] = step
        fd = (pm.heights(x + e) @ weights - pm.heights(x - e) @ weights) / (2.0 * step)
        rel = abs(fd - grad[k]) / max(abs(fd), abs(grad[k]), 1e-9)
        worst = max(worst, rel)
        print(f"variable {k:2d}: analytic {grad[k]: .8e}, central {fd: .8e}, relative {rel:.1e}")
    print(f"{pm.n_vars} variables, {int((pm.heights(x) > 0).sum())} columns covered; the worst relative difference {worst:.1e}")
    if worst > 1e-6:
        raise SystemExit("the derivatives disagree")


if __name__ == "__main__":
    if "--check" in sys.argv[1:]:
        _check()
