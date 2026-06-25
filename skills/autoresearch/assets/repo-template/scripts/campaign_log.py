#!/usr/bin/env python3
"""Append campaign events and render an interactive autoresearch report."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LOG_NAME = "campaign_events.jsonl"
REPORT_NAME = "report.html"
NODE_RE = re.compile(r"^(?P<op>[^:]+):\s+(?P<tag>.+)$")
METRIC_RE = re.compile(r"\[primary_metric=([^\]]+)\]")


def repo_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return Path(result.stdout.strip())


def run_git(root: Path, args: list[str], check: bool = False) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout


def run_paths(root: Path, task: str, run_tag: str) -> tuple[Path, Path, Path, Path]:
    run_root = root / "runs" / task / run_tag
    return (
        run_root,
        run_root / "campaign.json",
        run_root / LOG_NAME,
        run_root / REPORT_NAME,
    )


def utc_now() -> tuple[str, float]:
    epoch = time.time()
    stamp = datetime.fromtimestamp(epoch, timezone.utc).isoformat(timespec="seconds")
    return stamp, epoch


def read_text(path: str | None) -> str:
    if not path:
        return ""
    p = Path(path)
    if not p.is_file():
        return ""
    return " ".join(p.read_text(encoding="utf-8", errors="replace").split())


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_events(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    if not path.is_file():
        return events
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            events.append(event)
    return events


def parse_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def metric_direction(campaign: dict[str, Any]) -> str:
    raw = str(campaign.get("metric_direction") or campaign.get("direction") or "")
    raw = raw.lower()
    if raw in {"minimize", "min", "lower", "smaller", "down"}:
        return "minimize"
    return "maximize"


def better(a: float, b: float | None, direction: str) -> bool:
    if b is None:
        return True
    if direction == "minimize":
        return a < b
    return a > b


def improvement_delta(value: float, previous: float | None, direction: str) -> float | None:
    if previous is None:
        return None
    if direction == "minimize":
        return previous - value
    return value - previous


def score_for_scale(value: float, direction: str) -> float:
    return -value if direction == "minimize" else value


def fmt_number(value: float | None) -> str:
    if value is None:
        return ""
    if abs(value) >= 1000 or (abs(value) < 0.001 and value != 0):
        return f"{value:.3e}"
    return f"{value:.4g}"


def parse_trailers(body: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in body.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower()
        if key in {"pair", "parent", "hypothesis", "finding"}:
            out[key] = value.strip()
    return out


def parse_subject(subject: str) -> tuple[str, str, float | None]:
    match = NODE_RE.match(subject)
    op = match.group("op").strip() if match else "node"
    tag = match.group("tag").strip() if match else subject
    metric = None
    metric_match = METRIC_RE.search(tag)
    if metric_match:
        metric = parse_float(metric_match.group(1))
        status = "ok" if metric is not None else "crash"
    elif "[RUNNING]" in tag:
        status = "running"
    elif "[BUGGY]" in tag:
        status = "crash"
    else:
        status = "unknown"
    return op, status, metric


def git_nodes(root: Path, task: str, run_tag: str, run_root: Path) -> list[dict[str, Any]]:
    ref_prefix = f"refs/heads/agent/{task}/{run_tag}/"
    refs = [
        line.strip()
        for line in run_git(root, ["for-each-ref", "--format=%(refname:short)", ref_prefix]).splitlines()
        if line.strip()
    ]
    nodes: list[dict[str, Any]] = []
    for branch in refs:
        out = run_git(
            root,
            ["show", "-s", "--format=%H%x1f%h%x1f%ct%x1f%cI%x1f%s%x1f%B", branch],
            check=True,
        )
        parts = out.split("\x1f", 5)
        if len(parts) != 6:
            continue
        sha, short_sha, epoch_raw, iso_time, subject, body = [part.strip() for part in parts]
        op, status, metric = parse_subject(subject)
        trailers = parse_trailers(body)
        artifact = run_root / short_sha
        node = {
            "id": f"n{len(nodes) + 1}",
            "sha": sha,
            "short_sha": short_sha,
            "branch": branch,
            "epoch": parse_float(epoch_raw) or 0.0,
            "time": iso_time,
            "subject": subject,
            "op": op,
            "status": status,
            "metric": metric,
            "pair": trailers.get("pair", ""),
            "parent": trailers.get("parent", ""),
            "hypothesis": trailers.get("hypothesis", ""),
            "finding": trailers.get("finding", ""),
            "artifact": str(artifact) if artifact.exists() else "",
        }
        nodes.append(node)
    nodes.sort(key=lambda n: (n["epoch"], n["short_sha"]))
    for idx, node in enumerate(nodes, start=1):
        node["index"] = idx
        node["label"] = f"I{idx}"
    return nodes


def parent_map(nodes: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_sha: dict[str, dict[str, Any]] = {}
    for node in nodes:
        by_sha[node["sha"]] = node
        by_sha[node["short_sha"]] = node
    return by_sha


def find_parent(node: dict[str, Any], by_sha: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    parent = node.get("parent") or ""
    if not parent:
        return None
    if parent in by_sha:
        return by_sha[parent]
    for sha, candidate in by_sha.items():
        if sha.startswith(parent) or parent.startswith(sha):
            return candidate
    return None


def enrich_nodes(nodes: list[dict[str, Any]], direction: str) -> None:
    best: float | None = None
    by_sha = parent_map(nodes)
    for node in nodes:
        metric = node.get("metric")
        parent = find_parent(node, by_sha)
        parent_metric = parent.get("metric") if parent else None
        node["parent_id"] = parent.get("id") if parent else ""
        node["improved_parent"] = (
            isinstance(metric, float)
            and isinstance(parent_metric, float)
            and better(metric, parent_metric, direction)
        )
        node["raised_best"] = isinstance(metric, float) and better(metric, best, direction)
        if isinstance(metric, float) and better(metric, best, direction):
            previous = best
            best = metric
            node["best_delta"] = improvement_delta(metric, previous, direction)
        else:
            node["best_delta"] = None


def stable_lane(node: dict[str, Any], lane_count: int) -> int:
    seed = f"{node.get('pair','')}:{node.get('op','')}:{node.get('short_sha','')}"
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % lane_count


def compact(text: str, limit: int = 70) -> str:
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def text_lines(text: str, width: int = 32, max_lines: int = 3) -> list[str]:
    words = (text or "").split()
    lines: list[str] = []
    cur: list[str] = []
    for word in words:
        if sum(len(x) for x in cur) + len(cur) + len(word) > width and cur:
            lines.append(" ".join(cur))
            cur = [word]
            if len(lines) >= max_lines:
                break
        else:
            cur.append(word)
    if cur and len(lines) < max_lines:
        lines.append(" ".join(cur))
    if not lines:
        return [""]
    return lines


def svg_path(points: list[tuple[float, float]]) -> str:
    if not points:
        return ""
    parts = [f"M {points[0][0]:.1f} {points[0][1]:.1f}"]
    for x, y in points[1:]:
        parts.append(f"L {x:.1f} {y:.1f}")
    return " ".join(parts)


def render_report(root: Path, task: str, run_tag: str) -> Path:
    run_root, campaign_path, log_path, report_path = run_paths(root, task, run_tag)
    run_root.mkdir(parents=True, exist_ok=True)
    campaign = load_json(campaign_path)
    events = load_events(log_path)
    nodes = git_nodes(root, task, run_tag, run_root)
    direction = metric_direction(campaign)
    enrich_nodes(nodes, direction)

    width, height = 1440, 980
    left, right = 70, 60
    x_min = left
    x_max = width - right
    top_mid = 350
    lane_gap = 52
    lanes = [-3, -2, -1, 0, 1, 2, 3]
    bottom_top, bottom_bottom = 635, 895
    all_epochs = [float(n["epoch"]) for n in nodes if n.get("epoch")] + [
        float(e["epoch"]) for e in events if parse_float(e.get("epoch")) is not None
    ]
    if all_epochs:
        start_epoch = min(all_epochs)
        end_epoch = max(all_epochs)
    else:
        start_epoch = time.time()
        end_epoch = start_epoch + 1
    use_index_x = not nodes or end_epoch - start_epoch < 60

    def x_for_epoch(epoch: float, index: int) -> float:
        if use_index_x:
            span = max(1, len(nodes) - 1)
            return x_min + ((index - 1) / span) * (x_max - x_min) if len(nodes) > 1 else (x_min + x_max) / 2
        return x_min + ((epoch - start_epoch) / max(1.0, end_epoch - start_epoch)) * (x_max - x_min)

    for node in nodes:
        node["x"] = x_for_epoch(float(node["epoch"]), int(node["index"]))
        lane = lanes[stable_lane(node, len(lanes))]
        if node["status"] == "running":
            lane = 0
        node["y"] = top_mid + lane * lane_gap

    ok_nodes = [n for n in nodes if isinstance(n.get("metric"), float)]
    scores = [score_for_scale(float(n["metric"]), direction) for n in ok_nodes]
    if scores:
        lo, hi = min(scores), max(scores)
        if lo == hi:
            lo -= 1.0
            hi += 1.0
    else:
        lo, hi = 0.0, 1.0

    def y_for_metric(metric: float) -> float:
        score = score_for_scale(metric, direction)
        return bottom_bottom - ((score - lo) / max(1e-9, hi - lo)) * (bottom_bottom - bottom_top)

    edge_svg: list[str] = []
    green_edge_svg: list[str] = []
    by_id = {n["id"]: n for n in nodes}
    for node in nodes:
        parent = by_id.get(str(node.get("parent_id")))
        if not parent:
            continue
        x1, y1, x2, y2 = parent["x"], parent["y"], node["x"], node["y"]
        mid_y = min(y1, y2) - 90
        klass = "edge"
        path = (
            f"M {x1:.1f} {y1:.1f} "
            f"C {x1:.1f} {mid_y:.1f}, {x2:.1f} {mid_y:.1f}, {x2:.1f} {y2:.1f}"
        )
        edge_svg.append(f'<path class="{klass}" d="{path}"/>')
        if node.get("improved_parent") or node.get("raised_best"):
            green_edge_svg.append(f'<path class="inspiration" d="{path}"/>')

    node_svg: list[str] = []
    for node in nodes:
        classes = ["node"]
        if node.get("raised_best"):
            classes.append("raised")
        if node["status"] == "crash":
            classes.append("crash")
        elif node["status"] == "running":
            classes.append("running")
        title = html.escape(f'{node["label"]} {node["op"]} {node["short_sha"]}')
        node_svg.append(
            f'<g class="{" ".join(classes)}" data-node="{node["id"]}" tabindex="0">'
            f"<title>{title}</title>"
            f'<circle class="halo" cx="{node["x"]:.1f}" cy="{node["y"]:.1f}" r="14"/>'
            f'<circle class="ring" cx="{node["x"]:.1f}" cy="{node["y"]:.1f}" r="9"/>'
            f'<circle class="dot" cx="{node["x"]:.1f}" cy="{node["y"]:.1f}" r="4"/>'
            f'<text class="node-label" x="{node["x"]:.1f}" y="{node["y"] - 17:.1f}">{html.escape(node["label"])}</text>'
            "</g>"
        )

    grid_svg = []
    for frac, label in [(0.0, "0"), (0.5, "50%"), (1.0, "100%")]:
        y = bottom_bottom - frac * (bottom_bottom - bottom_top)
        grid_svg.append(f'<line class="grid-line" x1="{x_min}" x2="{x_max}" y1="{y:.1f}" y2="{y:.1f}"/>')
        grid_svg.append(f'<text class="axis-label" x="{x_min - 12}" y="{y + 4:.1f}" text-anchor="end">{label}</text>')

    step_points: list[tuple[float, float]] = []
    fill_path = ""
    raised_points: list[dict[str, Any]] = []
    best_metric: float | None = None
    prev_x = x_min
    prev_y = bottom_bottom
    if ok_nodes:
        step_points.append((x_min, bottom_bottom))
        for node in ok_nodes:
            metric = float(node["metric"])
            if better(metric, best_metric, direction):
                y = y_for_metric(metric)
                x = float(node["x"])
                step_points.append((x, prev_y))
                step_points.append((x, y))
                prev_x, prev_y = x, y
                best_metric = metric
                raised_points.append(node)
        step_points.append((x_max, prev_y))
        fill_path = svg_path(step_points + [(x_max, bottom_bottom), (x_min, bottom_bottom)])
    step_path = svg_path(step_points)

    annotation_svg: list[str] = []
    for i, node in enumerate(raised_points[-6:]):
        x, y = float(node["x"]), y_for_metric(float(node["metric"]))
        annotation_svg.append(
            f'<g class="metric-point" data-node="{node["id"]}" tabindex="0">'
            f'<circle class="metric-halo" cx="{x:.1f}" cy="{y:.1f}" r="20"/>'
            f'<circle class="ring" cx="{x:.1f}" cy="{y:.1f}" r="10"/>'
            f'<circle class="dot" cx="{x:.1f}" cy="{y:.1f}" r="4"/>'
            "</g>"
        )
        label_y = y + (58 if i % 2 else -54)
        delta = node.get("best_delta")
        delta_text = "" if delta is None else f" ({fmt_number(delta)} improvement)"
        lines = text_lines(f'{node["label"]} {node.get("pair") or node.get("hypothesis")}', 38, 2)
        annotation_svg.append(f'<text class="metric-note" x="{x:.1f}" y="{label_y:.1f}" text-anchor="middle">')
        for j, line in enumerate(lines):
            annotation_svg.append(f'<tspan x="{x:.1f}" dy="{0 if j == 0 else 17}">{html.escape(line)}</tspan>')
        annotation_svg.append(
            f'<tspan class="metric-delta" x="{x:.1f}" dy="18">{html.escape(fmt_number(node["metric"]))}{html.escape(delta_text)}</tspan>'
        )
        annotation_svg.append("</text>")

    if not nodes:
        node_svg.append(
            f'<text class="empty" x="{width / 2:.1f}" y="{top_mid:.1f}" text-anchor="middle">'
            "No idea nodes yet. Run the campaign to populate this report."
            "</text>"
        )

    elapsed_hours = max(0.0, (end_epoch - start_epoch) / 3600.0)
    details = {
        node["id"]: {
            "label": node["label"],
            "sha": node["short_sha"],
            "branch": node["branch"],
            "op": node["op"],
            "status": node["status"],
            "metric": fmt_number(node["metric"]),
            "pair": node.get("pair") or "",
            "hypothesis": node.get("hypothesis") or "",
            "finding": node.get("finding") or "",
            "artifact": node.get("artifact") or "",
            "parent": node.get("parent") or "",
            "time": node.get("time") or "",
        }
        for node in nodes
    }
    details_json = json.dumps(details, sort_keys=True).replace("<", "\\u003c").replace("&", "\\u0026")
    recent_events = events[-16:]
    event_items = "\n".join(
        f"<li><code>{html.escape(str(e.get('event', 'event')))}</code> "
        f"{html.escape(str(e.get('slot', '')))} "
        f"{html.escape(str(e.get('message', '') or e.get('status', '') or ''))}</li>"
        for e in recent_events
    )
    if not event_items:
        event_items = "<li>No logged events yet.</li>"

    metric_name = campaign.get("metric_name") or "primary_metric"
    title = f"{task}/{run_tag} autoresearch report"
    html_doc = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f5f4ef;
      --ink: #30322f;
      --muted: #7c817a;
      --line: #c9cac2;
      --soft: #e7e7dc;
      --green: #64d28e;
      --green-dark: #17663b;
      --panel: #ffffff;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      background: var(--bg);
      font-family: Georgia, "Times New Roman", serif;
    }}
    main {{
      width: min(1500px, calc(100% - 32px));
      margin: 0 auto;
      padding: 24px 0 40px;
    }}
    .legend {{
      display: flex;
      align-items: center;
      gap: 32px;
      flex-wrap: wrap;
      color: #5d625d;
      font-size: 18px;
      margin: 4px 0 14px;
    }}
    .legend span {{ display: inline-flex; align-items: center; gap: 9px; }}
    .legend em {{ font-style: italic; }}
    .legend-dot, .legend-ring {{
      width: 20px;
      height: 20px;
      border-radius: 50%;
      border: 2px solid var(--line);
      display: inline-block;
      position: relative;
      background: #fff;
    }}
    .legend-dot:after, .legend-ring:after {{
      content: "";
      position: absolute;
      left: 6px;
      top: 6px;
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: #2d302d;
    }}
    .legend-ring {{ outline: 3px solid rgba(100, 210, 142, 0.8); }}
    .legend-curve {{
      width: 42px;
      height: 16px;
      border-top: 3px solid var(--green);
      border-radius: 50%;
      transform: rotate(-18deg);
    }}
    .chart-wrap {{
      overflow-x: auto;
      border: 1px solid #e2e0d7;
      background: #fbfaf5;
    }}
    svg {{ display: block; min-width: {width}px; width: 100%; height: auto; }}
    .axis-main {{ stroke: #272a27; stroke-width: 4; stroke-linecap: round; }}
    .grid-line {{ stroke: #d7d6ca; stroke-dasharray: 4 7; }}
    .edge {{ fill: none; stroke: rgba(88, 92, 84, 0.28); stroke-width: 2; }}
    .inspiration {{ fill: none; stroke: rgba(100, 210, 142, 0.58); stroke-width: 2; }}
    .node, .metric-point {{ cursor: pointer; outline: none; }}
    .halo, .metric-halo {{ fill: transparent; stroke: transparent; }}
    .node:hover .halo, .node:focus .halo, .metric-point:hover .metric-halo, .metric-point:focus .metric-halo {{
      fill: rgba(100, 210, 142, 0.12);
      stroke: rgba(100, 210, 142, 0.35);
    }}
    .ring {{ fill: #fff; stroke: #a5a79e; stroke-width: 2; }}
    .raised .ring, .metric-point .ring {{ stroke: var(--green); stroke-width: 3; }}
    .crash .ring {{ stroke: #b9a2a2; }}
    .running .ring {{ stroke-dasharray: 3 3; }}
    .dot {{ fill: #2f332f; stroke: #fff; stroke-width: 1.5; }}
    .node-label, .axis-label {{ fill: #8a8d86; font-size: 14px; }}
    .empty {{ fill: #8a8d86; font-size: 20px; }}
    .axis-title {{
      fill: #888b84;
      font-size: 18px;
      font-style: italic;
    }}
    .metric-fill {{ fill: rgba(100, 210, 142, 0.20); }}
    .metric-step {{ fill: none; stroke: var(--green); stroke-width: 3; }}
    .metric-note {{ fill: #30322f; font-size: 16px; }}
    .metric-delta {{ fill: var(--green-dark); font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-weight: 700; }}
    .panel {{
      display: grid;
      grid-template-columns: minmax(0, 1.4fr) minmax(260px, 0.6fr);
      gap: 16px;
      margin-top: 16px;
    }}
    .detail, .events {{
      min-width: 0;
      padding: 16px;
      border: 1px solid #e2e0d7;
      background: var(--panel);
      border-radius: 8px;
      box-shadow: 0 10px 28px rgba(48, 50, 47, 0.06);
    }}
    h1 {{ margin: 0 0 4px; font-size: 26px; }}
    h2 {{ margin: 0 0 10px; font-size: 20px; }}
    .meta {{ color: var(--muted); font-size: 14px; margin-bottom: 12px; }}
    dl {{ display: grid; grid-template-columns: 120px minmax(0, 1fr); gap: 8px 12px; margin: 0; }}
    dt {{ color: var(--muted); }}
    dd {{ margin: 0; overflow-wrap: anywhere; }}
    .events ul {{ margin: 0; padding-left: 20px; }}
    .events li {{ margin: 7px 0; color: #555a54; }}
    code {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.92em; }}
    @media (max-width: 900px) {{
      .panel {{ grid-template-columns: 1fr; }}
      .legend {{ gap: 14px; font-size: 15px; }}
    }}
  </style>
</head>
<body>
<main>
  <h1>{html.escape(title)}</h1>
  <div class="meta">metric: {html.escape(str(metric_name))} ({html.escape(direction)}), nodes: {len(nodes)}, elapsed: {elapsed_hours:.2f} h</div>
  <div class="legend">
    <span><i class="legend-dot"></i> each dot = an idea node</span>
    <span><i class="legend-ring"></i> green ring = raised campaign-best score</span>
    <span><i class="legend-curve"></i> green curve = parent inspiration</span>
    <span><em>click any dot to read the idea</em></span>
  </div>
  <div class="chart-wrap">
  <svg viewBox="0 0 {width} {height}" role="img" aria-label="Autoresearch idea graph and metric timeline">
    <line class="axis-main" x1="{x_min - 18}" x2="{x_max}" y1="{top_mid}" y2="{top_mid}"/>
    {"".join(edge_svg)}
    {"".join(green_edge_svg)}
    {"".join(node_svg)}
    {"".join(grid_svg)}
    <text class="axis-title" x="22" y="{(bottom_top + bottom_bottom) / 2:.1f}" transform="rotate(-90 22 {(bottom_top + bottom_bottom) / 2:.1f})">campaign-best {html.escape(str(metric_name))}</text>
    <text class="axis-title" x="{width / 2:.1f}" y="{height - 22}" text-anchor="middle">research wall-clock time -></text>
    {'<path class="metric-fill" d="' + fill_path + ' Z"/>' if fill_path else ''}
    {'<path class="metric-step" d="' + step_path + '"/>' if step_path else ''}
    {"".join(annotation_svg)}
  </svg>
  </div>
  <section class="panel">
    <div class="detail">
      <h2 id="detail-title">Select an idea node</h2>
      <div id="detail-meta" class="meta">Click any dot in the graph or metric curve.</div>
      <dl>
        <dt>Pair</dt><dd id="detail-pair"></dd>
        <dt>Hypothesis</dt><dd id="detail-hypothesis"></dd>
        <dt>Finding</dt><dd id="detail-finding"></dd>
        <dt>Artifact</dt><dd id="detail-artifact"></dd>
      </dl>
    </div>
    <div class="events">
      <h2>Recent Log Events</h2>
      <ul>{event_items}</ul>
    </div>
  </section>
</main>
<script type="application/json" id="node-data">{details_json}</script>
<script>
const nodes = JSON.parse(document.getElementById('node-data').textContent);
const title = document.getElementById('detail-title');
const meta = document.getElementById('detail-meta');
const pair = document.getElementById('detail-pair');
const hypothesis = document.getElementById('detail-hypothesis');
const finding = document.getElementById('detail-finding');
const artifact = document.getElementById('detail-artifact');
function showNode(id) {{
  const n = nodes[id];
  if (!n) return;
  title.textContent = `${{n.label}} ${{n.op}} ${{n.sha}}`;
  meta.textContent = `status=${{n.status}} metric=${{n.metric || "n/a"}} branch=${{n.branch}} time=${{n.time}}`;
  pair.textContent = n.pair || "n/a";
  hypothesis.textContent = n.hypothesis || "n/a";
  finding.textContent = n.finding || "n/a";
  artifact.textContent = n.artifact || "n/a";
}}
document.querySelectorAll('[data-node]').forEach((el) => {{
  el.addEventListener('click', () => showNode(el.dataset.node));
  el.addEventListener('keydown', (ev) => {{
    if (ev.key === 'Enter' || ev.key === ' ') {{
      ev.preventDefault();
      showNode(el.dataset.node);
    }}
  }});
}});
const first = Object.keys(nodes)[0];
if (first) showNode(first);
</script>
</body>
</html>
"""
    tmp_path = report_path.with_suffix(".html.tmp")
    tmp_path.write_text(html_doc, encoding="utf-8")
    tmp_path.replace(report_path)
    return report_path


def log_event(args: argparse.Namespace) -> Path:
    root = repo_root()
    run_root, campaign_path, log_path, _ = run_paths(root, args.task, args.run_tag)
    run_root.mkdir(parents=True, exist_ok=True)
    stamp, epoch = utc_now()
    event: dict[str, Any] = {
        "event": args.event,
        "ts": stamp,
        "epoch": epoch,
        "task": args.task,
        "run_tag": args.run_tag,
    }
    for key in ("slot", "op", "parent", "branch", "sha", "status", "primary_metric", "round", "message"):
        value = getattr(args, key)
        if value not in (None, ""):
            event[key] = value
    file_values = {
        "pair": args.pair or read_text(args.pair_file),
        "hypothesis": args.hypothesis or read_text(args.hypothesis_file),
        "finding": args.finding or read_text(args.finding_file),
    }
    event.update({key: value for key, value in file_values.items() if value})
    if args.data_json:
        event["data"] = json.loads(args.data_json)
    if campaign_path.is_file():
        campaign = load_json(campaign_path)
        event.setdefault("metric_name", campaign.get("metric_name"))
        event.setdefault("metric_direction", campaign.get("metric_direction"))
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, sort_keys=True) + "\n")
    if not args.no_render:
        render_report(root, args.task, args.run_tag)
    return log_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    log = sub.add_parser("log", help="append one campaign event")
    log.add_argument("--task", required=True)
    log.add_argument("--run-tag", required=True)
    log.add_argument("--event", required=True)
    log.add_argument("--slot")
    log.add_argument("--op")
    log.add_argument("--parent")
    log.add_argument("--branch")
    log.add_argument("--sha")
    log.add_argument("--status")
    log.add_argument("--primary-metric")
    log.add_argument("--round")
    log.add_argument("--message")
    log.add_argument("--pair")
    log.add_argument("--hypothesis")
    log.add_argument("--finding")
    log.add_argument("--pair-file")
    log.add_argument("--hypothesis-file")
    log.add_argument("--finding-file")
    log.add_argument("--data-json")
    log.add_argument("--no-render", action="store_true")

    render = sub.add_parser("render", help="render report.html from git state and event log")
    render.add_argument("--task", required=True)
    render.add_argument("--run-tag", required=True)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "log":
        path = log_event(args)
        print(f"campaign_log: appended {path}")
    elif args.command == "render":
        path = render_report(repo_root(), args.task, args.run_tag)
        print(f"campaign_log: wrote {path}")
    else:
        parser.error("unknown command")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"campaign_log: {exc}", file=sys.stderr)
        raise
