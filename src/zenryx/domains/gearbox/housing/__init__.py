"""The gearbox housing's final workflow, its own code only (LOP-33): the stages the final recipe
runs, moved from `prototypes/first_loop/` with only the functions, and the branches of them, that
the recipe executes (traced by running the prototype on the reference design). The prototypes keep
every other approach.

- `cup`: the rooms each half holds, and the cup (outside and inside) drawn round them.
- `mesh`: watertight meshes and their booleans (manifold3d), the field's contour.
- `walls`: the least walls and the protected interfaces as signed distances, the run's metal beyond
  its least walls.
- `columns`: a height-field run's columns drawn as smooth members (outline and free end).
- `draw`: the design drawn from the run's field.
"""

from __future__ import annotations

import time


def say(text: str) -> None:
    """A line of the stage's log, timed as the prototypes' (`[HH:MM:SS] text`): the flow reads notes
    after "] "."""
    print(f"[{time.strftime('%H:%M:%S')}] {text}", flush=True)
