#!/usr/bin/env python3
"""Update the profile README with GitHub Linguist language statistics."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


OWNER = os.environ.get("GITHUB_OWNER", "RobbieFaLL")
README = Path(__file__).resolve().parents[1] / "README.md"
START_MARKER = "<!-- LANGUAGES:START -->"
END_MARKER = "<!-- LANGUAGES:END -->"
API_ROOT = "https://api.github.com"


def get_json(url: str) -> object:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "RobbieFaLL-profile-readme",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        with urlopen(Request(url, headers=headers), timeout=30) as response:
            return json.load(response)
    except (HTTPError, URLError) as error:
        raise RuntimeError(f"GitHub API request failed for {url}: {error}") from error


def repositories() -> list[dict[str, object]]:
    page = 1
    result: list[dict[str, object]] = []
    while True:
        data = get_json(
            f"{API_ROOT}/users/{OWNER}/repos"
            f"?per_page=100&page={page}&type=owner&sort=full_name"
        )
        if not isinstance(data, list):
            raise RuntimeError("GitHub returned an unexpected repository response.")
        result.extend(repo for repo in data if isinstance(repo, dict))
        if len(data) < 100:
            return result
        page += 1


def language_totals() -> dict[str, int]:
    totals: dict[str, int] = {}
    for repo in repositories():
        full_name = repo.get("full_name")
        if not isinstance(full_name, str):
            continue
        data = get_json(f"{API_ROOT}/repos/{full_name}/languages")
        if not isinstance(data, dict):
            raise RuntimeError(f"Unexpected language response for {full_name}.")
        for language, bytes_count in data.items():
            if isinstance(language, str) and isinstance(bytes_count, int):
                totals[language] = totals.get(language, 0) + bytes_count
    if not totals:
        raise RuntimeError("No GitHub Linguist language data was returned.")
    return totals


def progress_bar(percentage: float, width: int = 20) -> str:
    filled = round(percentage / 100 * width)
    return "█" * filled + " " * (width - filled)


def language_section(totals: dict[str, int]) -> str:
    total = sum(totals.values())
    rows = []
    bars = []
    for language, bytes_count in sorted(
        totals.items(), key=lambda item: (-item[1], item[0])
    ):
        percentage = bytes_count / total * 100
        rows.append(f"| {language} | {percentage:.1f}% |")
        bars.append(f"{language:<16} {progress_bar(percentage)} {percentage:.1f}%")

    return "\n".join(
        [
            START_MARKER,
            "## Languages used across my repositories",
            "",
            "These percentages are calculated automatically from GitHub's "
            "Linguist language statistics across my repositories.",
            "",
            "| Language | Share |",
            "| --- | ---: |",
            *rows,
            "",
            "```text",
            *bars,
            "```",
            "",
            "_Updated automatically by GitHub Actions._",
            END_MARKER,
        ]
    )


def update_readme(section: str) -> None:
    content = README.read_text(encoding="utf-8")
    start = content.find(START_MARKER)
    end = content.find(END_MARKER)
    if start == -1 or end == -1 or end < start:
        raise RuntimeError(
            f"README must contain matching {START_MARKER} and {END_MARKER} markers."
        )
    end += len(END_MARKER)
    README.write_text(content[:start] + section + content[end:], encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the generated section without changing README.md.",
    )
    args = parser.parse_args()

    try:
        section = language_section(language_totals())
        if args.dry_run:
            print(section)
        else:
            update_readme(section)
    except RuntimeError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
