"""Generic task evaluation dispatcher for the autoresearch toolkit.

Task-specific scoring lives in a task pack. Candidate programs may call this
wrapper when they want a stable root-level command, but the harness itself only
requires candidates to print `primary_metric: <float>`.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task_dir", required=True, type=Path)
    parser.add_argument("task_args", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    script = args.task_dir / "evaluate.py"
    if not script.is_file():
        raise SystemExit(f"task evaluate.py not found: {script}")

    cmd = [sys.executable, str(script)]
    if args.task_args:
        cmd.extend(args.task_args)
    raise SystemExit(subprocess.call(cmd))


if __name__ == "__main__":
    main()
