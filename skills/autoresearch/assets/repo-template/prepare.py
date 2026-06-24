"""Generic task preparation dispatcher for the autoresearch toolkit.

Task-specific setup lives in a task pack, usually `tasks/<slug>/prepare.py` or
`examples/<slug>/prepare.py`. This wrapper is a convenience entrypoint that
forwards to the selected task's preparation script.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task_dir", required=True, type=Path)
    parser.add_argument("--out_dir", required=True, type=Path)
    parser.add_argument("task_args", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    script = args.task_dir / "prepare.py"
    if not script.is_file():
        raise SystemExit(f"task prepare.py not found: {script}")

    cmd = [sys.executable, str(script), "--out_dir", str(args.out_dir)]
    if args.task_args:
        cmd.extend(args.task_args)
    raise SystemExit(subprocess.call(cmd))


if __name__ == "__main__":
    main()
