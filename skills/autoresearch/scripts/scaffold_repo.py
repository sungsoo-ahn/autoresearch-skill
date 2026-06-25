#!/usr/bin/env python3
"""Scaffold and git-initialize a generic autoresearch repository."""
from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = SKILL_DIR / "assets" / "repo-template"
ADAPTERS_DIR = SKILL_DIR / "assets" / "adapters"
DEFAULT_BRANCH = "agent/root"
DEFAULT_GIT_USER_NAME = "Autoresearch Skill"
DEFAULT_GIT_USER_EMAIL = "autoresearch@example.invalid"
SAFE_EXISTING_TARGET_ENTRIES = {".omx", ".DS_Store"}
INITIAL_COMMIT_MESSAGE = [
    "Create a bootstrap-ready autoresearch harness",
    (
        "Scaffold the task-neutral campaign runtime so task packs can be added, "
        "validated, and bootstrapped from agent/root."
    ),
    (
        "Constraint: Generated repositories need a clean root commit before "
        "campaign worktrees are created."
    ),
    "Confidence: high",
    "Scope-risk: narrow",
    "Tested: scaffold_repo.py copied the bundled template and initialized git.",
    "Co-authored-by: OmX <omx@oh-my-codex.dev>",
]


def _ignore(include_csp: bool):
    def inner(directory: str, names: list[str]) -> set[str]:
        ignored = {
            "__pycache__",
            ".git",
            ".omx",
            ".DS_Store",
            "data",
            "runs",
            ".worktrees",
            ".slots",
            ".venv",
            ".base-venv",
            "repo_structure_report.html",
        }
        if not include_csp and Path(directory).name == "examples":
            ignored.add("csp")
        return {name for name in names if name in ignored or name.endswith(".pyc")}

    return inner


def _target_ready(path: Path, force: bool) -> list[str]:
    if not path.exists():
        return []
    if not path.is_dir():
        raise SystemExit(f"target exists and is not a directory: {path}")
    entries = sorted(child.name for child in path.iterdir())
    blockers = [name for name in entries if name not in SAFE_EXISTING_TARGET_ENTRIES]
    if blockers and not force:
        raise SystemExit(
            f"target is not empty: {path}\n"
            f"Blocking entries: {', '.join(blockers)}\n"
            "Re-run with --force only after confirming overwrites are acceptable."
        )
    return [name for name in entries if name in SAFE_EXISTING_TARGET_ENTRIES]


def _rewrite_readme_title(target: Path, name: str | None) -> None:
    if not name:
        return
    readme = target / "README.md"
    if not readme.is_file():
        return
    lines = readme.read_text(encoding="utf-8").splitlines()
    if lines and lines[0].startswith("# "):
        lines[0] = f"# {name}"
        readme.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _run(cmd: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            cmd,
            cwd=cwd,
            check=check,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError as exc:
        raise SystemExit(
            f"command not found: {cmd[0]}. Install it or pass --no-git."
        ) from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        message = f"command failed: {' '.join(cmd)}"
        if detail:
            message = f"{message}\n{detail}"
        raise SystemExit(message) from exc


def _git_has_config(target: Path, key: str) -> bool:
    result = _run(["git", "config", "--get", key], target, check=False)
    return result.returncode == 0 and bool(result.stdout.strip())


def _init_git(target: Path) -> None:
    if (target / ".git").exists():
        raise SystemExit(f"target already has a git repository: {target}")

    result = _run(["git", "init", "-b", DEFAULT_BRANCH], target, check=False)
    if result.returncode != 0:
        _run(["git", "init"], target)
        _run(["git", "checkout", "-B", DEFAULT_BRANCH], target)

    if not _git_has_config(target, "user.name"):
        _run(["git", "config", "user.name", DEFAULT_GIT_USER_NAME], target)
    if not _git_has_config(target, "user.email"):
        _run(["git", "config", "user.email", DEFAULT_GIT_USER_EMAIL], target)

    _run(["git", "add", "."], target)
    cmd = ["git", "commit"]
    for paragraph in INITIAL_COMMIT_MESSAGE:
        cmd.extend(["-m", paragraph])
    _run(cmd, target)


def _copy_adapter(target: Path, adapter: str) -> None:
    if adapter == "none":
        return
    adapter_dir = ADAPTERS_DIR / adapter
    if not adapter_dir.is_dir():
        raise SystemExit(f"adapter not found: {adapter}")
    shutil.copytree(adapter_dir, target, dirs_exist_ok=True, ignore=_ignore(True))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--name", default=None)
    parser.add_argument("--include-csp-example", action="store_true")
    parser.add_argument("--adapter", default="none", choices=("none", "claude"))
    parser.add_argument("--no-git", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if not TEMPLATE_DIR.is_dir():
        raise SystemExit(f"repo template not found: {TEMPLATE_DIR}")

    target = args.target.resolve()
    preserved_entries = _target_ready(target, args.force)
    target.mkdir(parents=True, exist_ok=True)

    shutil.copytree(
        TEMPLATE_DIR,
        target,
        dirs_exist_ok=True,
        ignore=_ignore(args.include_csp_example),
    )
    _rewrite_readme_title(target, args.name)
    _copy_adapter(target, args.adapter)

    if not args.no_git:
        _init_git(target=target)

    print(f"scaffolded autoresearch repo: {target}")
    if preserved_entries:
        print(f"preserved existing runtime entries: {', '.join(preserved_entries)}")
    if not args.no_git:
        print(f"initialized git branch: {DEFAULT_BRANCH}")
        print(f"created initial commit: {INITIAL_COMMIT_MESSAGE[0]}")
    if args.adapter != "none":
        print(f"included adapter: {args.adapter}")
    if args.include_csp_example:
        print("included example: examples/csp")
    print("next: create or review tasks/<slug>/, then run scripts/validate_task.sh")


if __name__ == "__main__":
    main()
