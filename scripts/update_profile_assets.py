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
PORTRAIT_PATHS = {
    "light": ASSETS_DIR / "profile-portrait-light.txt",
    "dark": ASSETS_DIR / "profile-portrait-dark.txt",
}
PORTRAIT_EDGE_PATH = ASSETS_DIR / "profile-portrait-edge.txt"
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


def ascii_layer(lines: list[str], css_class: str) -> str:
    return "\n".join(
        (
            f'<text x="48" y="{101 + index * 9.45:.2f}" class="{css_class}" '
            f'xml:space="preserve">{html.escape(line)}</text>'
        )
        for index, line in enumerate(lines)
    )


def render_svg(
    palette: Palette,
    stats: dict[str, int | str],
    portrait_lines: list[str],
    edge_lines: list[str],
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
  <desc id="desc">A terminal-style summary of Muhammad Azeem Rao's product engineering, architecture, AI, full-stack, cloud, and leadership experience.</desc>
  <defs>
    <clipPath id="portrait-clip">
      <rect x="38" y="84" width="330" height="408" rx="22"/>
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
    <pattern id="portrait-grid" width="16" height="16" patternUnits="userSpaceOnUse">
      <path d="M16 0H0V16" fill="none" stroke="{palette.border}" stroke-opacity="0.32" stroke-width="0.7"/>
    </pattern>
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
    .ascii {{ font: 600 9.4px ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace; fill: {palette.text}; opacity: 0.88; }}
    .ascii-edge {{ font: 700 9.4px ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace; fill: {palette.accent}; opacity: 0.55; }}
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
    <rect x="38" y="84" width="330" height="408" fill="{palette.panel_alt}"/>
    <rect x="38" y="84" width="330" height="408" fill="url(#portrait-glow)"/>
    <rect x="38" y="84" width="330" height="408" fill="url(#portrait-grid)"/>
    {ascii_layer(portrait_lines, "ascii")}
    {ascii_layer(edge_lines, "ascii-edge")}
  </g>
  <rect x="38" y="84" width="330" height="408" rx="22" fill="none" stroke="{palette.border}" stroke-width="2"/>
  <path d="M52 112 V98 H66 M340 98 H354 V112 M52 464 V478 H66 M340 478 H354 V464" fill="none" stroke="{palette.accent}" stroke-width="3"/>
  {text_node(42, 520, "ARCHITECT → BUILD → LEAD", "eyebrow")}
  {text_node(42, 548, "Product-minded engineering", "subhead")}
  {text_node(42, 572, "with an AI-native edge.", "subhead")}

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

    required_portrait_files = [*PORTRAIT_PATHS.values(), PORTRAIT_EDGE_PATH]
    missing = [path for path in required_portrait_files if not path.exists()]
    if missing:
        print(
            "Missing profile portrait data: " + ", ".join(str(path) for path in missing),
            file=sys.stderr,
        )
        return 1

    stats = FALLBACK_STATS if args.offline else fetch_stats()
    portraits = {
        theme: path.read_text(encoding="utf-8").splitlines()
        for theme, path in PORTRAIT_PATHS.items()
    }
    edge_lines = PORTRAIT_EDGE_PATH.read_text(encoding="utf-8").splitlines()

    changed: list[str] = []
    for palette in PALETTES:
        output = ASSETS_DIR / f"profile-console-{palette.name}.svg"
        if save_if_changed(
            output,
            render_svg(palette, stats, portraits[palette.name], edge_lines),
        ):
            changed.append(output.relative_to(ROOT).as_posix())

    if changed:
        print("Updated " + ", ".join(changed))
    else:
        print("Profile console is already current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
