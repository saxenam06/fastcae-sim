# Python CAE tooling on native Windows

Compiled 2026-10-04 by a web-research subagent from PyPI JSON, official docs and GitHub. **Not yet re-verified.**
Assumes x64 Windows; ARM64 is unverified. `[n]` refers to the URL list at the end.

| Tool | Latest (date) | Python | Windows pip wheels? | Notes |
|---|---|---|---|---|
| CadQuery | 2.8.0 (2026-06-21) [1] | >=3.11 | Pure wheel; needs cadquery-ocp 7.9.3.1.1 (cp310-314 win_amd64) and vtk==9.6.2 [2] | `Shape.tessellate(tol, angTol)` returns (verts, tris) [3]. STEP/STL via `export`; STL defaults 0.001/0.1 [4]. A clean Windows install may need the VC++ x64 redistributable (third-party report) [5] |
| build123d | 0.13.0 (2026-09-21) [6] | >=3.11,<3.15 | Pure wheel; needs cadquery-ocp-novtk 8.0.1.0.0 (cp311-314 win_amd64) [7] | `export_step`, `export_stl(tolerance, angular_tolerance)` [8]; `Shape.tessellate` [9]. CadQuery pins OCP<8 [1] while build123d needs OCP 8 [6], so use one per environment |
| gmsh | 4.15.2 (2026-03-24) [11] | any | win_amd64 only [11] | OCC bundled [12]. `occ.importShapes` reads STEP/IGES/BREP [12], then `occ.synchronize`, `addPhysicalGroup`, `mesh.generate(3)` [13]. `import gmsh` calls `signal.signal` and **fails off the main thread** [14] |
| scikit-fem | 12.0.2 (2026-06-05) [15] | >=3.10 | Pure [15] | 3D modal: ex21 (MeshTet.load of .msh, ElementTetP2, `solver_eigen_scipy_sym`) [16]. 3D elasticity: ex11; eigenproblem: ex03 [17]. Robin BC: ex17 (2D) [18]. Default solver SuperLU: a 64k-DOF solve takes 63 s, 512k fails [19]. Pardiso is 2.5× faster on Windows [20]. About 100k DOF is comfortable (estimate). `Mesh.load` uses meshio and maps gmsh:physical to subdomains [21] |
| dolfinx | – | – | None; no PyPI project [22] | Windows needs Docker or WSL2. conda packages are "beta" and have no PETSc [23] |
| Exudyn | 1.11.0 (2026-08-05) [24] | cp310-314 | win_amd64 [24] | `FEMinterface`: ImportMeshFromNGsolve, ImportFromAbaqusInputFile, Read{Mass,Stiffness}MatrixFrom{Abaqus,Ansys}, ComputeHurtyCraigBamptonModes → ObjectFFRFreducedOrder [25]. NGSolve 6.2.2608: cp310-314 win_amd64 [26] |
| PyChrono | conda-forge 10.0.0 (2026-04-02) [27] | – | None; conda only [28] | PyPI "pychrono" is an unrelated library [29] |
| CalculiX / Code_Aster | ccx 2.23 (2025-10-19) [30] | – | ccx is not on pip: zip from dhondt.de [31] | pyccx 0.2.0 needs gmsh>=4.14 [32]; pygccx is GitHub-only [33]. Code_Aster: official Windows route is WSL2 [34]; a third-party native MSI exists [35] |
| pyvista / trimesh / meshio / open3d | 0.49.0 [36] / 5.1.1 [38] / 5.3.5 (2024-01-31) [41] / 0.20.0 [43] | >=3.10 (meshio >=3.8) | pyvista, trimesh, meshio pure; vtk 9.6.2 [37] and open3d cp310-314 win_amd64 | trimesh: `sample_surface`, `sample_surface_even`, `volume_mesh` [39]; `proximity.signed_distance` treats inside as positive [40]. meshio has open NumPy-2 issues [42], so prefer gmsh API → MeshTet |
| pysdf / mesh-to-sdf | 0.1.9 (2023) / 0.0.15 (2024) | – | pysdf is sdist only (C++ build) [44]; mesh-to-sdf needs OpenGL and has a Windows bug [45] | Use trimesh instead |
| mcp | 2.3.0 (2026-10-02) [46] | >=3.10 | Pure; pywin32 on Windows [46] | FastMCP is renamed `MCPServer` (`mcp.server`); `mcp.run(transport="stdio")`; v2 runs sync `def` tools **on worker threads** [47]. Schemas come from type hints and pydantic models; BaseModel returns give outputSchema [48]. v1.30.0 is still maintained [49] |
| claude-agent-sdk | 0.2.163 (2026-09-30) [50] | >=3.10 | **None for 0.2.160–0.2.163** (issue open) [51]; 0.2.159 has win_amd64 [52] | Pin `==0.2.159`, or use `--only-binary` [53], or the sdist plus a native Claude Code on PATH [54]. `@tool` + `create_sdk_mcp_server`, then `mcp_servers={...}`, `allowed_tools=["mcp__s__tool"]`; Python `@tool` drops structuredContent [55] |
| uv | 0.12.23 (2026-10-03) [66] | – | – | See notes |

## Notes

- **Agent SDK authentication.**
  - The Agent SDK reads the Claude Code CLI login (claude.ai `/login`). If `ANTHROPIC_API_KEY` is set, it takes precedence [56].
  - Third parties may not offer claude.ai login [57], so public-repo users bring their own credential.
  - Billing policy for SDK and `claude -p` usage under subscriptions is in flux [58].
- **Scripting `claude -p`.**
  - Flags: `--mcp-config`, `--strict-mcp-config`, `--allowedTools`, `--output-format json`, `--max-turns`,
    `--max-budget-usd`, `--no-session-persistence` [59].
  - `--bare` ignores the subscription login [60], and `CLAUDE_CODE_OAUTH_TOKEN` is not read by `--bare` [61].
  - MCP results over 25k tokens spill to a file [62], so return summaries or paths.
- **uv.**
  - `UV_PYTHON_INSTALL_DIR` can only be set as an environment variable [63].
  - `UV_CACHE_DIR` or `cache-dir` sets the cache; keep the cache and venv on the same drive [64].
  - `UV_PROJECT_ENVIRONMENT` moves `.venv` [63].
  - `uv python install --no-bin --no-registry` avoids writing to PATH and the registry [65].
- **Threading trap.** gmsh must be imported on the main thread, but MCP v2 runs tools on worker threads, so mesh in a subprocess.
- **Unverified:**
  - the exact `importShapes` signature;
  - whether CadQuery and build123d actually clash on disk;
  - meshio under NumPy 2;
  - pysdf on Windows;
  - the DOF estimate.

## Recommendation

- **Python 3.12 x64.**
  - numpy 2.5.3 and scipy 1.18.1 require >=3.12 [67].
  - Every binary dependency has cp312 win_amd64 wheels.
  - Python 3.13 is the fallback; avoid 3.14 for now.
- **Forces conda, WSL or Docker:** FEniCSx/dolfinx, PyChrono, and Code_Aster's official route. Everything else installs natively.
- **Still to check:** ROSS (Petrobras rotordynamics library) on Windows.

## URLs

1. https://pypi.org/pypi/cadquery/2.8.0/json
2. https://pypi.org/pypi/cadquery-ocp/7.9.3.1.1/json
3. https://raw.githubusercontent.com/CadQuery/cadquery/master/cadquery/occ_impl/shapes.py
4. https://cadquery.readthedocs.io/en/latest/importexport.html
5. https://github.com/lhundley42/LucasCad/issues/5
6. https://pypi.org/pypi/build123d/0.13.0/json
7. https://pypi.org/pypi/cadquery-ocp-novtk/8.0.1.0.0/json
8. https://build123d.readthedocs.io/en/latest/import_export.html
9. https://raw.githubusercontent.com/gumyr/build123d/dev/src/build123d/topology/shape_core.py
10. https://pypi.org/pypi/cadquery-ocp-proxy/8.0.1.0.0/json
11. https://pypi.org/pypi/gmsh/4.15.2/json
12. https://github.com/Starcube-Technologies/gmsh-wheels ; https://gmsh.info/doc/texinfo/gmsh.html
13. https://docs.fenicsproject.org/dolfinx/main/python/demos/demo_gmsh.html
14. https://github.com/mikedh/trimesh/issues/1987
15. https://pypi.org/pypi/scikit-fem/12.0.2/json
16. https://raw.githubusercontent.com/kinnala/scikit-fem/master/docs/examples/ex21.py
17. https://scikit-fem.readthedocs.io/en/latest/listofexamples.html
18. https://raw.githubusercontent.com/kinnala/scikit-fem/master/docs/examples/ex17.py
19. https://raw.githubusercontent.com/kinnala/scikit-fem/master/README.md
20. https://github.com/kinnala/scikit-fem/issues/690
21. https://raw.githubusercontent.com/kinnala/scikit-fem/master/skfem/io/meshio.py
22. https://pypi.org/simple/fenics-dolfinx/
23. https://github.com/FEniCS/dolfinx
24. https://pypi.org/pypi/exudyn/1.11.0/json
25. https://exudyn.readthedocs.io/en/stable/docs/RST/pythonUtilities/FEM.html
26. https://pypi.org/pypi/ngsolve/6.2.2608/json
27. https://anaconda.org/conda-forge/pychrono
28. https://api.projectchrono.org/pychrono_installation.html
29. https://pypi.org/pypi/pychrono/json
30. https://en.wikipedia.org/wiki/Calculix
31. https://www.dhondt.de
32. https://pypi.org/pypi/pyccx/json
33. https://github.com/calculix/pygccx
34. https://github.com/simvia-tech/Videos/blob/main/%5BTips%20&%20Tricks%5D%20Install%20Salome_Meca%20on%20Windows%20using%20WSL/Commands%20used%20in%20the%20video.md
35. https://simulease.com/download
36. https://pypi.org/pypi/pyvista/0.49.0/json
37. https://pypi.org/pypi/vtk/9.6.2/json
38. https://pypi.org/pypi/trimesh/5.1.1/json
39. https://trimesh.org/trimesh.sample.html
40. https://trimesh.org/trimesh.proximity.html
41. https://pypi.org/pypi/meshio/5.3.5/json
42. https://github.com/nschloe/meshio/issues?q=numpy+2
43. https://pypi.org/pypi/open3d/0.20.0/json
44. https://github.com/sxyu/sdf ; https://pypi.org/pypi/pysdf/json
45. https://github.com/marian42/mesh_to_sdf
46. https://pypi.org/pypi/mcp/2.3.0/json
47. https://py.sdk.modelcontextprotocol.io/migration/
48. https://py.sdk.modelcontextprotocol.io/servers/structured-output/index.md
49. https://pypi.org/pypi/mcp/1.30.0/json
50. https://pypi.org/pypi/claude-agent-sdk/0.2.163/json
51. https://github.com/anthropics/claude-agent-sdk-python/issues/1349
52. https://pypi.org/pypi/claude-agent-sdk/0.2.159/json
53. https://github.com/UiPath/skills/pull/3605
54. https://code.claude.com/docs/en/agent-sdk/troubleshooting
55. https://code.claude.com/docs/en/agent-sdk/custom-tools
56. https://code.claude.com/docs/en/errors
57. https://code.claude.com/docs/en/agent-sdk/quickstart
58. https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan
59. https://code.claude.com/docs/en/cli-reference
60. https://code.claude.com/docs/en/headless
61. https://code.claude.com/docs/en/authentication
62. https://code.claude.com/docs/en/mcp
63. https://docs.astral.sh/uv/reference/storage/
64. https://docs.astral.sh/uv/concepts/cache/ ; https://docs.astral.sh/uv/reference/settings/
65. https://github.com/astral-sh/uv/blob/main/changelogs/0.8.x.md
66. https://pypi.org/project/uv/
67. https://pypi.org/pypi/scipy/1.18.1/json ; https://pypi.org/pypi/numpy/json
