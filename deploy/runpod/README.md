# The GPU on RunPod, serverless (PLT-12)

The loop's heavy work (the optimisation, FE, the whole `run_final.py`) runs on a RunPod serverless worker: a GPU billed
by the second only while a job runs, nothing while idle. The engineer's aim (15 October): a 16 GB card, so the voxels can
go finer than the laptop's 4 mm.

## How it works

```
laptop / cloud session                       RunPod
  git push  ───────────────────────────────▶  GitHub (the code at a ref)
  submit.py final ──▶ endpoint ──▶ worker (image: deps only) ──▶ git checkout <ref> on the network volume
                                                │                 run_final.py / one script, on the GPU
                                                └─ data/first_loop/, web/src/records/ stay on the volume
  sync.sh pull <pattern> ◀── S3 API ◀─────────── the volume (no worker started for this)
```

- **The image** (`Dockerfile`) holds only the environment: Python 3.12 and every extra from `uv.lock` (cupy, nvmath's
  cuDSS, CadQuery, gmsh, manifold3d, VTK), plus `tetgen`, `pymeshlab` (outside `uv.lock`, as on the laptop) and the
  `runpod` SDK. GitHub Actions builds it (`.github/workflows/runpod-image.yml`) when `uv.lock`, `pyproject.toml` or this
  folder changes, as `ghcr.io/saxenam06/zenryx-worker:<commit>`.
- **The code** is not in the image. Each job checks out its git ref onto the network volume (`handler.py`), so a code
  change needs a push, never a rebuild. A ref whose `uv.lock` differs from the image's is refused: rebuild first.
- **The data** lives on the network volume: `/runpod-volume/fastcae-sim/data/first_loop/` and `web/src/records/`, as on
  the laptop. A later job sees an earlier one's runs (`--run <stem>` redraws one).
- **One job at a time** (max workers 1): the checkout is shared. A lock file on the volume refuses a second job beside one.
- **Portability:** the pipeline was Windows-only in three places (the venv's `Scripts/python.exe`, `taskkill`, the
  memory guard's PowerShell); `prototypes/first_loop/hostenv.py` now answers each on Linux too, and the laptop behaves as
  before.

## Setting it up, once

1. **The image.** Push this folder to GitHub; the `runpod-image` workflow builds and pushes
   `ghcr.io/saxenam06/zenryx-worker:<commit sha>` (about 20 minutes, several GB). Either make the package public
   (GitHub → Packages → zenryx-worker → settings; it holds no code, only the dependencies and the handler) or give RunPod
   a registry credential (RunPod → Settings → Container Registry Auth: user `saxenam06`, a GitHub token with
   `read:packages`).
2. **A GitHub token for the worker** (the repository is checked out at each job): a fine-grained token, this repository
   only, *Contents: read-only*. Store it as a RunPod secret (Settings → Secrets) named `github_token`.
3. **A network volume** (Storage → New Network Volume): 50 GB, in a datacenter that has both the S3-compatible API
   (EU-CZ-1, EU-RO-1, EUR-IS-1, EUR-NO-1, US-CA-2, US-GA-2, US-IL-1, US-KS-2, US-MD-1, US-MO-1) and 16 GB GPUs in stock.
   The volume ties the endpoint to that datacenter.
4. **The endpoint** (Serverless → New Endpoint → Import from registry / custom image):
   - image `ghcr.io/saxenam06/zenryx-worker:<commit sha>` (pin the sha, not `latest`, so a run is reproducible);
   - GPU: **16 GB** (A4000, A4500, RTX 4000 Ada), with 24 GB as a second choice when 16 GB is out of stock;
   - active workers **0**, max workers **1**, idle timeout 5 s, FlashBoot on;
   - **execution timeout 7200 s** (a full run took 25 minutes at 4 mm on the laptop; finer voxels take longer);
   - container disk 20 GB; the network volume from step 3;
   - environment: `GITHUB_TOKEN = {{ RUNPOD_SECRET_github_token }}`.
5. **On the laptop** (Git Bash; never in git, `.env` is ignored):
   ```
   export RUNPOD_API_KEY=...            # RunPod → Settings → API Keys
   export RUNPOD_ENDPOINT_ID=...        # the endpoint's id
   export RUNPOD_VOLUME_ID=...          # for sync.sh
   export RUNPOD_DATACENTER=EU-RO-1     # the volume's
   export AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=...   # RunPod → Settings → S3 API Keys
   ```
   `sync.sh` needs the AWS CLI (`pip install awscli` or the installer).

## Using it

```
python deploy/runpod/submit.py health                                   # the endpoint answers
python deploy/runpod/submit.py script contract_layout.py                # the layout from the contract, onto the volume (CPU, ~1 min)
python deploy/runpod/submit.py script fast_factor_check.py 4            # the GPU path's own check, on the worker's card
bash   deploy/runpod/sync.sh push '*baseline2_lw8*'                     # an earlier run, to redraw it there
python deploy/runpod/submit.py final --run <baseline2_lw8's run stem> --design rp_parity   # draw and judge, ~10 min
python deploy/runpod/submit.py final --force                            # the whole recipe: optimisation, drawing, FE, grade
bash   deploy/runpod/sync.sh pull '*rp_parity*'                         # its files, for the UI and the docs
```

`submit.py` waits and prints each progress line (minutes, the GPU's peak memory, the log's last line); `--no-wait`, then
`submit.py status <job>`. Every job's log is `data/first_loop/runpod_<job>.log` on the volume. A job's result names the
GPU, its **peak memory** and the files it wrote. `--env LOOP_X=v` sets a setting for one job only (a check, never the
baseline: a setting changes through the recipe).

### Only the optimisation on RunPod

A finer voxel costs memory only in the optimiser (`topo_free.py`): the drawing is on a fixed 1 mm grid, and FE's mesh is
coarsened to 7 mm triangles whatever the voxel. So the laptop's 8 GB card can still draw and judge a finer run:

```
python deploy/runpod/submit.py script topo_free.py <budget kg> <voxel mm> <the recipe's optimiser arguments>   # the GPU part alone
bash   deploy/runpod/sync.sh pull '*<run stem>*'
.venv/Scripts/python.exe prototypes/first_loop/run_final.py --run <run stem>            # draw, FE, grade on the laptop
```

The worker is billed by the second whether its GPU is busy or not, so the CPU stages of a full run (drawing, TetGen,
castability, pictures: about 10 of its 25 minutes) cost about $0.10 at the 16 GB rate. Running everything on the worker
is what lets a cloud session (no GPU, no `data/`) run the whole workflow without the laptop.

## Finer voxels: what to measure before choosing

- **The scaling:** the voxels go as the cube of 1/size: 4 → 3.5 mm is ×1.5, → 3 mm ×2.4, → 2.5 mm ×4.1, → 2 mm ×8. The
  sparse factor's memory grows faster than the unknowns. On the laptop's 8 GB card 3.5 mm was the finest and 3 mm did not
  fit (CLAUDE.md); a 16 GB card should hold 3 mm, 2 mm likely needs 48-80 GB. The first jobs' peak memory says.
- **The rules are written in cubes as well as mm.** The flange is 8 mm, "two whole cubes each side" at 4 mm; the least
  width (`--least-width 8`) is the fullest 2 x 2 block of columns. At 3 mm the flange is 2.67 cubes and the block 6 mm;
  at 2 mm both stay whole (4 cubes, and the opening's block would need to be 4 x 4 for 8 mm). So a finer voxel is a new
  recipe version, scouted and judged, with the engineer's word (CLAUDE.md: settings change only through the recipe).
- **FE's own ceiling** (`fe.CEILING_DOF`, `fe.MESHED_MOST`: 2.18 M unknowns, the laptop's 8 GB card and 16 GB of host
  memory) is unchanged by default. `LOOP_CEILING_DOF` and `LOOP_MESHED_MOST` set another on the worker once measured; it
  is the FE budget, so the engineer's word first. FE's mesh does not depend on the voxel size (the surface is coarsened
  to 7 mm triangles), so the optimiser is where a finer voxel costs.
- **The cost:** 16 GB flex workers were about $0.00016 a second (about $0.58 an hour) on RunPod's pricing page in
  2026: a 25-minute run about $0.25. The network volume is billed by the GB-month whether used or not.

## What it cannot do yet

- Built here, not yet run on RunPod: the image has not been pulled by a worker, and no job has run. The first jobs above
  are its test (each step's result goes to the platform page's PLT-12 row).
- The pictures need a display: the handler starts Xvfb; the headless Edge screenshots (`web/tools/shot.mjs`) stay on the
  laptop.
