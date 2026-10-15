"""PROTOTYPE (PLT-5, LOP-33) - the API the UI's Run button calls (`zenryx.api.server`), on port 8030, with the final workflow's
heavy stages the prototype's (`engines.py`) until they are in `src/zenryx`, and the optimisation on RunPod unless `.env` says
`ZENRYX_OPTIMISE_ON=local` (`zenryx.workflow.remote`). A server: start it only on the engineer's word.

    .venv/Scripts/python.exe prototypes/first_loop/serve.py      (then `npm run dev` in web/, which proxies /api to it)"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
sys.path.insert(0, str(HERE))

from engines import PrototypeEngines  # noqa: E402

from zenryx.api.server import serve  # noqa: E402
from zenryx.workflow.remote import engines_for  # noqa: E402


def make_engines(out: Path):
    return engines_for(PrototypeEngines(out), out)


if __name__ == "__main__":
    serve(make_engines)
