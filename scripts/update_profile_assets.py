#!/usr/bin/env python3
"""Build the theme-aware profile console used by the GitHub profile README."""

from __future__ import annotations

import argparse
import html
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = ROOT / "assets"
PORTRAIT_BLOCKS_PATH = ASSETS_DIR / "profile-portrait-blocks.txt"
PORTRAIT_COLORS_PATH = ASSETS_DIR / "profile-portrait-colors.txt"
PORTRAIT_COLUMNS = 50
PORTRAIT_ROWS = 40
USERNAME = "mrmuhammadazeemrao"

FALLBACK_STATS = {
    "public_repos": 83,
    "followers": 4,
    "following": 10,
    "stars": 3,
    "forks": 7,
    "created_at": "2019-10-03T19:14:55Z",
}


@dataclass(frozen=True)
class Palette:
    name: str
    background: str
    panel: str
    panel_alt: str
    border: str
    text: str
    muted: str
    accent: str
    secondary: str
    success: str
    warm: str


PALETTES = (
    Palette(
        name="light",
        background="#FFFFFF",
        panel="#F6F8FA",
        panel_alt="#EEF2FF",
        border="#D0D7DE",
        text="#1F2328",
        muted="#57606A",
        accent="#0969DA",
        secondary="#8250DF",
        success="#1A7F37",
        warm="#BC4C00",
    ),
    Palette(
        name="dark",
        background="#0D1117",
        panel="#161B22",
        panel_alt="#111827",
        border="#30363D",
        text="#E6EDF3",
        muted="#8B949E",
        accent="#58A6FF",
        secondary="#A371F7",
        success="#3FB950",
        warm="#F0883E",
    ),
)


def api_json(path: str) -> Any:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{USERNAME}-profile-readme",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(f"https://api.github.com{path}", headers=headers)
    try:
        with urlopen(request, timeout=30) as response:
            return json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"GitHub API request failed for {path}: {exc}") from exc


def fetch_stats() -> dict[str, int | str]:
    user = api_json(f"/users/{USERNAME}")
    repos: list[dict[str, Any]] = []

    page = 1
    while True:
        batch = api_json(
            f"/users/{USERNAME}/repos?type=owner&sort=updated&per_page=100&page={page}"
        )
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1

    return {
        "public_repos": int(user["public_repos"]),
        "followers": int(user["followers"]),
        "following": int(user["following"]),
        "stars": sum(int(repo["stargazers_count"]) for repo in repos),
        "forks": sum(int(repo["forks_count"]) for repo in repos),
        "created_at": str(user["created_at"]),
    }


def text_node(
    x: int,
    y: int,
    value: str,
    css_class: str,
    *,
    anchor: str | None = None,
) -> str:
    anchor_attr = f' text-anchor="{anchor}"' if anchor else ""
    return (
        f'<text x="{x}" y="{y}" class="{css_class}"{anchor_attr}>'
        f"{html.escape(value)}</text>"
    )


def info_row(y: int, label: str, value: str) -> str:
    return "\n".join(
        (
            text_node(430, y, label, "label"),
            f'<line x1="548" y1="{y - 6}" x2="1138" y2="{y - 6}" class="leader"/>',
            f'<rect x="574" y="{y - 22}" width="570" height="29" class="value-backdrop"/>',
            text_node(590, y, value, "value"),
        )
    )


def metric_card(x: int, value: str, label: str, palette: Palette) -> str:
    return f"""
    <g>
      <rect x="{x}" y="535" width="170" height="76" rx="14" class="metric-card"/>
      <rect x="{x}" y="535" width="5" height="76" rx="2.5" fill="{palette.accent}"/>
      {text_node(x + 20, 568, value, "metric-value")}
      {text_node(x + 20, 592, label.upper(), "metric-label")}
    </g>"""


def portrait_color(raw_color: str, palette: Palette) -> str:
    """Transform a source-photo color for legibility in the active theme."""
    red = int(raw_color[0:2], 16)
    green = int(raw_color[2:4], 16)
    blue = int(raw_color[4:6], 16)
    mean = (red + green + blue) / 3

    red = int(mean + (red - mean) * 0.58)
    green = int(mean + (green - mean) * 0.58)
    blue = int(mean + (blue - mean) * 0.58)

    if palette.name == "light":
        scale = 0.86 if mean > 175 else 0.95
        red = min(210, int(red * scale))
        green = min(210, int(green * scale))
        blue = min(210, int(blue * scale))
    else:
        red = min(235, 82 + int(red * 0.65))
        green = min(235, 82 + int(green * 0.65))
        blue = min(235, 82 + int(blue * 0.65))

    return f"#{red:02X}{green:02X}{blue:02X}"


def portrait_layer(
    block_lines: list[str],
    color_rows: list[list[str]],
    palette: Palette,
) -> str:
    """Render high-detail terminal art from Unicode quadrant-block glyphs."""
    nodes: list[str] = []
    for row, line in enumerate(block_lines):
        blocks = line.ljust(PORTRAIT_COLUMNS)
        for column, character in enumerate(blocks[:PORTRAIT_COLUMNS]):
            if character == " ":
                continue
            x = 28 + column * 7.65
            y = 76 + row * 10.25
            color = portrait_color(color_rows[row][column], palette)
            nodes.append(
                f'<text x="{x:.2f}" y="{y:.2f}" '
                f'class="portrait-cell" fill="{color}">{html.escape(character)}</text>'
            )
    return "\n".join(nodes)


def render_svg(
    palette: Palette,
    stats: dict[str, int | str],
    portrait_blocks: list[str],
    portrait_colors: list[list[str]],
) -> str:
    created_year = str(stats["created_at"])[:4]
    metric_cards = "\n".join(
        (
            metric_card(420, str(stats["public_repos"]), "public repos", palette),
            metric_card(605, str(stats["stars"]), "repo stars", palette),
            metric_card(790, str(stats["followers"]), "followers", palette),
            metric_card(975, created_year, "on GitHub since", palette),
        )
    )

    rows = "\n".join(
        (
            info_row(174, "role", "Lead Full-Stack & AI Engineer"),
            info_row(210, "scope", "Product · Architecture · Delivery · Leadership"),
            info_row(246, "experience", "8 years building and scaling web products"),
            info_row(282, "languages", "Ruby · Python · TypeScript · JavaScript · SQL"),
            info_row(318, "backend", "Rails · FastAPI · Django · Node.js · NestJS"),
            info_row(354, "frontend", "React · Remix · Next.js · Angular · Stimulus"),
            info_row(390, "agentic", "LLMs · MCP · RAG · tools · evals · guardrails"),
            info_row(426, "platform", "AWS · Azure · GCP · Docker · Kubernetes · CI/CD"),
        )
    )

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="640" viewBox="0 0 1200 640" role="img" aria-labelledby="title desc">
  <title id="title">Muhammad Azeem Rao engineering profile console</title>
  <desc id="desc">A close-up Unicode quadrant-block terminal portrait beside a summary of Muhammad Azeem Rao's product engineering, architecture, AI, full-stack, cloud, and leadership experience.</desc>
  <defs>
    <clipPath id="portrait-clip">
      <rect x="24" y="78" width="394" height="420" rx="22"/>
    </clipPath>
    <linearGradient id="accent-line" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="{palette.accent}"/>
      <stop offset="0.55" stop-color="{palette.secondary}"/>
      <stop offset="1" stop-color="{palette.success}"/>
    </linearGradient>
    <radialGradient id="portrait-glow" cx="50%" cy="38%" r="64%">
      <stop offset="0" stop-color="{palette.accent}" stop-opacity="0.14"/>
      <stop offset="0.72" stop-color="{palette.secondary}" stop-opacity="0.04"/>
      <stop offset="1" stop-color="{palette.panel_alt}" stop-opacity="0"/>
    </radialGradient>
    <filter id="shadow" x="-10%" y="-10%" width="120%" height="125%">
      <feDropShadow dx="0" dy="8" stdDeviation="10" flood-color="#000000" flood-opacity="0.16"/>
    </filter>
  </defs>
  <style>
    .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace; }}
    .titlebar {{ font: 600 16px ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace; fill: {palette.muted}; }}
    .eyebrow {{ font: 700 13px ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace; letter-spacing: 1.8px; fill: {palette.accent}; }}
    .headline {{ font: 700 28px ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace; fill: {palette.text}; }}
    .subhead {{ font: 500 16px ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace; fill: {palette.muted}; }}
    .label {{ font: 700 15px ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace; fill: {palette.warm}; }}
    .value {{ font: 500 17px ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace; fill: {palette.text}; }}
    .portrait-cell {{ font: 400 11px ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace; }}
    .metric-value {{ font: 800 26px ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace; fill: {palette.text}; }}
    .metric-label {{ font: 700 11px ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace; letter-spacing: 1px; fill: {palette.muted}; }}
    .leader {{ stroke: {palette.border}; stroke-width: 1; stroke-dasharray: 2 5; }}
    .value-backdrop {{ fill: {palette.background}; }}
    .metric-card {{ fill: {palette.panel}; stroke: {palette.border}; }}
  </style>

  <rect x="8" y="8" width="1184" height="624" rx="24" fill="{palette.background}" stroke="{palette.border}" filter="url(#shadow)"/>
  <path d="M8 64 H1192" stroke="{palette.border}"/>
  <circle cx="34" cy="36" r="7" fill="#FF5F57"/>
  <circle cx="58" cy="36" r="7" fill="#FEBC2E"/>
  <circle cx="82" cy="36" r="7" fill="#28C840"/>
  {text_node(108, 42, "$ ./whoami --profile --human", "titlebar")}
  <rect x="1018" y="23" width="142" height="26" rx="13" fill="{palette.panel}" stroke="{palette.border}"/>
  <circle cx="1037" cy="36" r="4.5" fill="{palette.success}"/>
  {text_node(1050, 41, "OPEN TO BUILD", "eyebrow")}

  <g clip-path="url(#portrait-clip)">
    <rect x="24" y="78" width="394" height="420" fill="{palette.panel_alt}"/>
    <rect x="24" y="78" width="394" height="420" fill="url(#portrait-glow)"/>
    {portrait_layer(portrait_blocks, portrait_colors, palette)}
  </g>
  <rect x="24" y="78" width="394" height="420" rx="22" fill="none" stroke="{palette.border}" stroke-width="2"/>
  <path d="M38 106 V92 H52 M390 92 H404 V106 M38 470 V484 H52 M390 484 H404 V470" fill="none" stroke="{palette.accent}" stroke-width="3"/>
  {text_node(28, 520, "ARCHITECT → BUILD → LEAD", "eyebrow")}
  {text_node(28, 548, "Product-minded engineering", "subhead")}
  {text_node(28, 572, "with an AI-native edge.", "subhead")}

  {text_node(430, 104, "MUHAMMAD@GITHUB", "eyebrow")}
  {text_node(430, 137, "Muhammad Azeem Rao", "headline")}
  {text_node(1138, 137, "mrmuhammadazeemrao", "subhead", anchor="end")}
  <rect x="430" y="151" width="708" height="3" rx="1.5" fill="url(#accent-line)"/>
  {rows}
  {text_node(430, 470, "SYSTEM SIGNAL", "eyebrow")}
  {text_node(1138, 470, "PUBLIC GITHUB DATA · AUTO-REFRESHED", "subhead", anchor="end")}
  {metric_cards}
</svg>
"""


def save_if_changed(path: Path, content: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.write_text(content, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Use checked-in fallback stats instead of calling the GitHub API.",
    )
    args = parser.parse_args()

    required_portrait_files = [PORTRAIT_BLOCKS_PATH, PORTRAIT_COLORS_PATH]
    missing = [path for path in required_portrait_files if not path.exists()]
    if missing:
        print(
            "Missing profile portrait data: " + ", ".join(str(path) for path in missing),
            file=sys.stderr,
        )
        return 1

    stats = FALLBACK_STATS if args.offline else fetch_stats()
    portrait_blocks = PORTRAIT_BLOCKS_PATH.read_text(encoding="utf-8").splitlines()
    portrait_colors = [
        line.split()
        for line in PORTRAIT_COLORS_PATH.read_text(encoding="utf-8").splitlines()
    ]
    if len(portrait_blocks) != PORTRAIT_ROWS or len(portrait_colors) != PORTRAIT_ROWS:
        print(f"Portrait data must contain {PORTRAIT_ROWS} rows", file=sys.stderr)
        return 1
    if any(len(line) > PORTRAIT_COLUMNS for line in portrait_blocks):
        print(f"Portrait rows cannot exceed {PORTRAIT_COLUMNS} columns", file=sys.stderr)
        return 1
    if any(len(row) != PORTRAIT_COLUMNS for row in portrait_colors):
        print(f"Portrait color rows must contain {PORTRAIT_COLUMNS} values", file=sys.stderr)
        return 1
    for row, line in enumerate(portrait_blocks):
        for column, character in enumerate(line.ljust(PORTRAIT_COLUMNS)):
            raw_color = portrait_colors[row][column]
            if character != " ":
                try:
                    int(raw_color, 16)
                except ValueError:
                    print(
                        f"Invalid portrait color at row {row + 1}, column {column + 1}",
                        file=sys.stderr,
                    )
                    return 1

    changed: list[str] = []
    for palette in PALETTES:
        output = ASSETS_DIR / f"profile-console-{palette.name}.svg"
        if save_if_changed(
            output,
            render_svg(palette, stats, portrait_blocks, portrait_colors),
        ):
            changed.append(output.relative_to(ROOT).as_posix())

    if changed:
        print("Updated " + ", ".join(changed))
    else:
        print("Profile console is already current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
