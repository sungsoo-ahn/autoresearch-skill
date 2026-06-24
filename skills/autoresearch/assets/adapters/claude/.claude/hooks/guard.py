#!/usr/bin/env python3
"""PreToolUse guard for unattended autoresearch campaigns.

The loop may run with broad tool permissions, so this hook hard-blocks edits to
the reusable harness, task packs, examples, data, and toolkit instructions. A
candidate-authoring agent should only edit `.worktrees/<slot>/candidate.py`,
extend its slot venv, and write runtime files under `.slots/` or `runs/`.
"""
import json
import re
import sys

PROTECTED_NAMES = {
    "evaluate.py",
    "prepare.py",
    "requirements.txt",
    "program.md",
    "contract.md",
}
PROTECTED_DIRS = {
    "scripts",
    ".claude",
    "toolkit",
    "examples",
    "data",
}


def deny(reason):
    sys.stderr.write("BLOCKED by guard.py: " + reason + "\n")
    sys.exit(2)


def path_protected(path):
    if not path:
        return False
    parts = path.replace("\\", "/").split("/")
    if "tasks" in parts and ".worktrees" not in parts:
        return False
    if parts[-1] in PROTECTED_NAMES:
        return True
    if ".worktrees" in parts and "tasks" in parts:
        return True
    return any(part in PROTECTED_DIRS for part in parts[:-1])


def main():
    data = json.loads(sys.stdin.read())
    tool = data.get("tool_name", "")
    ti = data.get("tool_input", {}) or {}

    if tool in ("Edit", "Write", "NotebookEdit", "MultiEdit"):
        path = ti.get("file_path") or ti.get("notebook_path") or ""
        if path_protected(path):
            deny("protected harness/task path is read-only: " + path)

    elif tool == "Bash":
        cmd = ti.get("command", "") or ""
        if re.search(r"(?:^|[\n;&|])\s*git\s+push\b", cmd):
            deny("git push is forbidden for the autonomous loop")
        protected_name_re = "|".join(re.escape(name) for name in PROTECTED_NAMES)
        if re.search(r">>?\s*\S*(?:" + protected_name_re + r")\b", cmd):
            deny("redirect into protected harness file is forbidden")
        if re.search(r">>?\s*(?:[^\s]*/)?(?:scripts|\.claude|toolkit|examples|data)/", cmd):
            deny("redirect into protected directory is forbidden")
        if re.search(
            r"(?:^|[\n;&|`(])\s*(?:cp|mv|sed\s+-\S*i)\s[^\n]*\b(?:" + protected_name_re + r")\b",
            cmd,
        ):
            deny("write-capable command targeting protected harness file")

    sys.exit(0)


try:
    main()
except Exception:
    sys.exit(0)
