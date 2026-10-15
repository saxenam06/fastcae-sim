# Li et al. 2022, boundary density evolution (BDE): a critical note

**12 October 2026, 20:00.** One of the reviewer's papers. Does it support optimising a smooth implicit boundary with shape rules in the loop, and would it fix our irregular housings? No to both: it is a density method with a deletion rule, and its smooth boundary is drawn after the run.

## 1. Citation and how it was read

Li X., Qin C., Wei P., Su C. (South China University of Technology): *A boundary density evolutionary topology optimization of continuum structures with smooth boundaries.* International Journal for Numerical Methods in Engineering 123(1), 158-179 (2022; online 30 October 2021). doi [10.1002/nme.6851](https://doi.org/10.1002/nme.6851).

**Not read in full.** Wiley refused every automated fetch (HTTP 403), and no open copy was found (OpenAlex: closed, no repository copy; Google Scholar: only paywalled or abstract pages). What was read:
- the abstract and the 42-item reference list (Crossref);
- **the first author's granted Chinese patent on the same method, which itself calls it BDE:** CN112100882B, filed 27 August 2020, granted 15 March 2024. Read in full (Google's translation checked against the Chinese; equations, tables and figures viewed in its PDF). Its two examples may not be the paper's;
- the authors' 2024 open-access paper that reuses BDE (Li, Zhu, Wei, Su, *IJSMDO* 15, 12), in full;
- second-hand: Fu, Long & Rolfe 2023 (*JOTA*), Liu et al. 2026 (*Computation*), Ježek et al. 2025 (arXiv 2512.06976; its v1 reference to this paper has wrong initials, title, issue and pages).

§2-6 therefore describe the method as patented; the paper's own "four static and one dynamic" examples were not seen.

## 2. Problem and representation

Minimum compliance under a volume limit; the dynamic example is probably an eigenfrequency (the paper cites Du & Olhoff 2007). One density per element on a structured mesh: 4-node squares in 2D, 8-node bricks in 3D. Every element starts at 1. The shape is a level set of the nodal strain energy, drawn once, after the run.

## 3. The method

1. Linear interpolation, no penalty: E(x) = E_min + x·(E0 − E_min).
2. Compliance sensitivity by the adjoint, filtered as in Sigmund's 99-line code, radius r_min in elements (1.5-3).
3. Update by optimality criteria with a move limit (the patent allows MMA or GCMMA; its examples use OC).
4. **The "density grading filter":** a threshold 0, 1/G_f, 2/G_f, … rises by 1/G_f each iteration, and every element at or below it is set to 0. The OC update is multiplicative, so a zeroed element stays at 0 (my reading; not stated). This is ESO's hard kill laid over a continuous update. The run ends with only 0 and 1 elements after about G_f iterations.
5. Optionally the 0/1 result is subdivided, 2×2 (2×2×2 in 3D), its displacements interpolated or solved once more.
6. Element strain energies x_e·u_eᵀk0u_e are averaged to the nodes and interpolated by the shape functions: Φ(o).
7. A level S is found by bisection until the volume equals the target. An element is solid when all its nodes' Φ exceed S, void when none do, otherwise its density is the share of a 20×20 sub-grid above S.
8. The design is the contour Φ = S (or the nodal density at 0.5), written as STL "for 3D printing".

## 4. What it controls

- **Smoothness:** only in the drawing, a bilinear contour between nodes. No curvature or perimeter term anywhere.
- **Least member:** only through the sensitivity filter, in elements. With r_min fixed at 2 elements, refining 60×40 to 300×200 gives more and thinner members (patent Table 3).
- **Greatest member, junctions:** nothing.
- **Casting:** nothing: no pull, draft, undercut or closed-wall rule.
- **Topology:** holes open only by deletion; material cannot return. The final contour also reclassifies any element its level crosses.
- **More than one constraint:** not shown; every example I saw has one volume limit.

## 5. Scale and cost

- 2D cantilever: 60×40 to 300×200 elements, 31-149 iterations, about G_f each time.
- 3D bridge (patent): half model, 52,800 bricks, 60 iterations, 2,375 s on an Intel i5 at 3.3 GHz (about 40 s an iteration). Subdivided to 421,400 elements for the drawing only.
- The references cite the 88-line and top3d MATLAB codes: probably MATLAB on a CPU (not stated).

## 6. Results (patent; 2D cantilever, volume 0.5, compliance c without units, iterations in brackets)

| Mesh | SIMP (p = 3) | BESO | Level set | BDE |
|---|---|---|---|---|
| 60×40 | 34.21 (120) | 32.31 (72) | 31.16 (100) | 31.32 (49) |
| 300×200 | 33.23 (120) | 32.43 (96) | 32.24 (78) | 32.11 (101) |

- 90×60: r_min 1.5/2/3 gave c = 31.47/31.43/31.70; G_f 30/50/100 gave 31.60/31.43/31.42 in 31/60/93 iterations. The layout changes with each setting.
- The convergence plot: the grey design reaches c ≈ 29 near iteration 12; the deletions bring it to about 31-32 by iteration 25.
- **The patent reports no stiffness for the smoothed shape**, so the smoothing step is unmeasured there (the paper's tables were not seen). In the 2024 follow-up the smoothed cells' Poisson's ratio drifted from the optimised value, and the authors re-tuned the level by hand, which removed 5.7-7.1 % of the volume.

## 7. Limitations

**Stated (patent):** high resolution needs a finer mesh and a larger G_f; 3D needs a coarse run, then subdivision. Ježek et al. add "computational complexity and restriction to structured meshes".

**Mine:**
- The level set is a display, not a design variable. "Smooth boundaries similar to LSM" means a smooth contour of an element result.
- The boundary step resembles Da et al.'s ETO (2018, cited by the paper), where a level set of nodal sensitivities defines the topology inside a BESO loop (as Fu et al. describe it; not read here). BDE applies it once, after the run.
- The comparison flatters BDE. SIMP's 34.21 counts grey elements at p = 3 (its 60×40 picture is grey); the level-set method beat BDE at 60×40 (31.16 against 31.32); and BDE's iteration count is a fixed schedule (≈ G_f), so "converges faster" is by construction.
- Two heuristics, G_f and r_min, set the result; no optimality argument covers the deletion.
- The 2024 follow-up writes the SIMP law with a penalty p (value not given): "no penalty" was not kept there.
- The smoothed 3D bridge (patent Fig. 15) has uneven, lumpy arches: the look we are trying to leave.

## 8. Code, data and licence

No code found (no repository; none in the patent or on the first author's page; the paper's own statement could not be read). The paper is closed access under Wiley's terms. The method is patented in China (CN112100882B, South China University of Technology). The 2024 follow-up is CC BY 4.0.

## 9. For our problem

- **Would it fix the irregular shape?** No. Ours is the layout and the members' form (broad low members, knots where they cross, wavy sides), not voxel steps, and we already contour smoothly (`LOOP_SDF`; [rho2sdf](../2026-10-12-smooth-extraction-rho2sdf.md)). BDE's contour keeps the layout, as rho2sdf does, and its own 3D example comes out organic.
- **Would it keep stiffness?** Unknown: nobody measured the smoothed shape. The volume is held and the boundary moves about an element, so a large loss is unlikely; no gain either. The deletion rule does not suit our bed and tilt constraints: an element deleted on the compliance's sensitivity cannot return when a seat's tilt needs it.
- **Against the reviewer's proposal:**
  - it supports keeping the optimised solid as the design (it writes the STL directly) and topology change by removal;
  - it does not support the rest: no implicit boundary as the design variable, no curvature penalty, thickness or junction limit, casting rule or plate-and-branch rule inside the loop.
- **The engineer's new rules.** BDE starts full and removes metal, which fits a fixed design space and no fixed shell. Nothing in it keeps a closed, oil-tight wall; without a fixed shell that needs its own constraint.
- **What it would take:** the grading filter is a few lines in our update; the strain-energy contour about a day (nodal averaging, bisection on the level, our marching cubes). Compute: one solve an iteration, G_f (50-150) iterations, as our 4 mm runs (about 300k voxels) cost today; the 2×2×2 subdivision for the contour (2.4 M cells) is light. 1 M voxels does not fit the 8 GB card's solver (3 mm voxels already did not); BDE does not change that.
- **The first small test (no optimisation run):** take `outcome_hf6_4mm_7.0kg`'s field, compute each voxel's peak-drive strain energy on the optimiser's own model (for tilt-held runs the Lagrangian's sensitivity is the honest field), average to the nodes, find the level that gives the same metal mass, contour it, draw it by the mesh route with the exact shell, and judge by FE and `castable.py` (a 3D contour ignores the pull) against its plain and `LOOP_SDF=3` drawings. Close the line if the members look the same; keep it only if the beds stay within rho2sdf's 8 % and the lumps visibly thin.

## 10. Sources

- Refused (HTTP 403): https://onlinelibrary.wiley.com/doi/epdf/10.1002/nme.6851, https://onlinelibrary.wiley.com/doi/full/10.1002/nme.6851
- Abstract, references, licence: https://api.crossref.org/works/10.1002/nme.6851; https://api.semanticscholar.org/graph/v1/paper/DOI:10.1002/nme.6851 (and its citations); https://api.openalex.org/works/https://doi.org/10.1002/nme.6851; versions: https://scholar.google.com/scholar?cluster=14985183880434922784
- The patent: https://patents.google.com/patent/CN112100882B/en, https://patents.google.com/patent/CN112100882B/zh, PDF https://patentimages.storage.googleapis.com/e1/94/6f/9c0cdb56ece764/CN112100882B.pdf
- The first author's page (lists the patent): https://faculty.scut.edu.cn/tmyjt/lxp7/main.htm
- Li, Zhu, Wei, Su 2024, doi 10.1051/smdo/2024011, read from https://web.archive.org/web/20240814121344/https://www.ijsmdo.org/articles/smdo/pdf/2024/01/smdo240024.pdf
- Fu, Long, Rolfe 2023: https://link.springer.com/content/pdf/10.1007/s10957-023-02222-3.pdf
- Liu et al. 2026: https://mdpi-res.com/d_attachment/computation/computation-14-00027/article_deploy/computation-14-00027.pdf
- Ježek et al. 2025: https://arxiv.org/html/2512.06976v1
