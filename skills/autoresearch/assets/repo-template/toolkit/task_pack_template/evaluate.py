"""Task-specific fixed evaluator template."""
from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run_dir", required=True)
    parser.parse_args()
    raise SystemExit("replace this template with task-specific evaluation")


if __name__ == "__main__":
    main()
