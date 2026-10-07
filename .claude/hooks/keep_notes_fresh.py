"""Copied from fastcae-v1:.claude/hooks/keep_notes_fresh.py on 2026-10-07; changed: the WORK folders and the run-output
folder (data/ instead of results/).

Keep the status pages fresh: while work goes on, the page of the feature being worked on
(docs/features/<feature>/status.md) - or the board, docs/status.md - is rewritten at least every
20 minutes, so a session that ends or loses its context without warning never leaves the team a
stale page (CLAUDE.md, "How the work is organised").

Run by Claude Code's hooks (.claude/settings.json, through .claude/hooks/run.sh), reading the
hook's input on stdin:

- **PostToolUse**: when the newest status page is older than :data:`FRESH_S` and work has happened
  since it was written, a reminder is handed to Claude (as a "block", which after a tool only
  delivers its reason) - at most every :data:`NAG_S`.
- **Stop**: the same condition holds the turn open until a page is rewritten - once: a turn
  already held open by this hook may end, so it can never loop.

A session that keeps a START HERE note in its own Claude memory is held to it the same way; a
session without one is not. Quiet when the pages are fresh, or when nothing has changed since
they were written; silent for subagents.
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
import time
from pathlib import Path

FRESH_S = 20 * 60
"""How old the newest status page may grow while work goes on."""
NAG_S = 5 * 60
"""How often, at most, the reminder repeats between tool calls."""
GRACE_S = 60
"""Work this soon after a page was written counts as noted in it."""

PROJECT = Path(__file__).resolve().parents[2]
WORK = ["src", "checks", "tools", "docs", "web/src"]
"""Where work shows: a file changed under any of these, in the project."""
SKIP = {"__pycache__", "node_modules", ".pytest_cache", ".ruff_cache"}


def status_pages() -> list[Path]:
    """The board and every feature's status page."""
    docs = PROJECT / "docs"
    return [docs / "status.md", *sorted((docs / "features").glob("*/status.md"))]


def newest(root: Path, pattern: str = "*") -> float:
    """The latest modification of any file under ``root`` matching ``pattern``; 0 when none."""
    latest = 0.0
    if not root.exists():
        return latest
    for path in root.rglob(pattern):
        if SKIP.intersection(path.parts) or not path.is_file():
            continue
        try:
            latest = max(latest, path.stat().st_mtime)
        except OSError:
            continue
    return latest


def start_here(memory: Path) -> Path | None:
    """The memory note the index names START HERE, if this session keeps one."""
    index = memory / "MEMORY.md"
    try:
        for line in index.read_text(encoding="utf-8").splitlines():
            if "START HERE" in line:
                found = re.search(r"\]\(([^)]+\.md)\)", line)
                if found:
                    return memory / found.group(1)
    except OSError:
        return None
    return None


def main() -> None:
    try:
        given = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        given = {}
    event = given.get("hook_event_name", "")
    session = str(given.get("session_id", "session"))
    transcript = Path(str(given.get("transcript_path", "")))
    # the main session's only: a read-only reviewer was once asked to rewrite the notes (2026-09-24)
    if given.get("agent_id") or transcript.parent.name == "subagents":
        return
    slug = transcript.parent.name if transcript.name else "project"
    memory = transcript.parent / "memory" if transcript.name else None
    note = start_here(memory) if memory is not None and memory.is_dir() else None

    now = time.time()
    scratch = Path(
        given.get("scratchpad_dir")
        or Path(tempfile.gettempdir()) / "claude" / slug / session / "scratchpad"
    )
    extra = [newest(PROJECT / "data", "campaign.json"), newest(scratch)]
    worked = max([newest(PROJECT / w) for w in WORK] + extra)
    # a status page is itself under docs/: writing docs is not work done since the pages
    worked_outside_docs = max([newest(PROJECT / w) for w in WORK if w != "docs"] + extra)

    stale = []
    pages = [p for p in status_pages() if p.exists()]
    if pages:
        page = max(pages, key=lambda p: p.stat().st_mtime)
        written = page.stat().st_mtime
        if now - written > FRESH_S and worked_outside_docs > written + GRACE_S:
            stale.append(
                f"the status pages (the newest, {page.relative_to(PROJECT).as_posix()}, "
                f"is {(now - written) / 60:.0f} min old)"
            )
    if note is not None:
        try:
            written = note.stat().st_mtime
            if now - written > FRESH_S and worked > written + GRACE_S:
                stale.append(f"your memory note {note.name} ({(now - written) / 60:.0f} min old)")
        except OSError:
            pass
    if not stale:
        return

    words = (
        "Stale, with work done since: " + "; ".join(stale) + ". Rewrite now the status page of "
        "the feature you are working on (docs/features/<feature>/status.md): Now - where each PBI "
        "stands, the runs launched (id, laptop, start, expected end), the exact next step - and "
        "What runs, Rules in force, Measured, Decisions and Open where they changed; the current "
        "state, not a log; the time in its header from `date`. The board (docs/status.md) when the "
        "feature's headline changed. Your START HERE memory note too, if you keep one."
    )
    if event == "Stop":
        if given.get("stop_hook_active"):
            return
        print(json.dumps({"decision": "block", "reason": words}))
        return
    mark = Path(tempfile.gettempdir()) / f"keep-notes-fresh-{session}.txt"
    try:
        last = float(mark.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        last = 0.0
    if now - last < NAG_S:
        return
    mark.write_text(str(now), encoding="utf-8")
    # after a tool the "block" undoes nothing - the tool has run; it hands Claude the reason
    print(json.dumps({"decision": "block", "reason": words}))


if __name__ == "__main__":
    main()
