#!/usr/bin/env bash
# Run one of this folder's hook scripts with the project's own Python, on Windows (Git Bash) or
# macOS/Linux:  bash "$CLAUDE_PROJECT_DIR/.claude/hooks/run.sh" keep_notes_fresh.py
# The hook's input arrives on stdin and passes through. With no project Python the hook is skipped,
# never an error.
dir="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
for py in "$dir/.venv/Scripts/python.exe" "$dir/.venv/bin/python"; do
  if [ -x "$py" ]; then
    exec "$py" "$dir/.claude/hooks/$1"
  fi
done
exit 0
