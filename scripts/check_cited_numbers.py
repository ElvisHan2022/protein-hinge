#!/usr/bin/env python3
"""Refuse to let a retired figure survive in the prose.

Numbers move whenever a lane is rebuilt. Prose citing the old ones does not
announce itself: the sentence still reads fine, the table still lines up, and
nothing errors. That is the same silent-error shape this project exists to
catch, so it gets the same treatment -- a mechanical check rather than care.

`scripts/build_paper_metrics.py` records each figure's superseded values under
`retired_values`. This script scans the documents for them.

  python3 scripts/check_cited_numbers.py           report findings, exit 0
  python3 scripts/check_cited_numbers.py --strict  exit 1 if any are found

Two escape hatches, because some retired numbers belong in the text:
  * files in HISTORICAL are skipped -- they are logs of what changed
  * a line carrying the marker below is skipped
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
METRICS = ROOT / "model_trace" / "paper_metrics.json"
MARKER = "numbers-ok"

DOCS = [
    "README.md", "CLAUDE.md", "site/mockup.html", "figures/workflow_dag.svg",
    "docs/PAPER_METHODS_OUTLINE.md", "docs/PROJECT_BRIEF.md",
    "docs/DEBRIEF_FOR_BYRON.md", "docs/HANDOFF_ELVIS_2026-08-24.md",
    "docs/SUBMISSION_CHECKLIST_0829.md", "docs/PITCH_DECK.md",
    "docs/VIDEO_SCRIPT.md", "docs/PLAIN_LANGUAGE_BRIEF.md",
]

# Deliberate records of what the numbers used to be.
HISTORICAL = {"docs/BUILD_NOTES.md"}

# A bare integer is not a citation when it is part of a URL, DOI, hash, date,
# CSS length, or SVG coordinate.
NOISE = re.compile(
    r"https?://|doi\.org|sha256|zenodo|NCT\d|\d{4}-\d{2}-\d{2}"
    r"|\d+px|[xy]\d?=\"|font-size|stroke|viewBox|padding|margin|width:|height:"
    r"|(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?[\s*]+\d{1,2}"
    r"|\d{1,2}(st|nd|rd|th)"
)


def main() -> int:
    strict = "--strict" in sys.argv
    if not METRICS.exists():
        print("paper_metrics.json missing -- run scripts/build_paper_metrics.py first")
        return 1
    metrics = json.loads(METRICS.read_text(encoding="utf-8"))
    retired = metrics.get("retired_values") or {}
    live = set((metrics.get("headline") or {}).values())

    # value -> the figures it used to represent
    wanted: dict[int, list[str]] = {}
    for figure, values in retired.items():
        for v in values:
            if v not in live:
                wanted.setdefault(v, []).append(figure)
    if not wanted:
        print("no retired values recorded yet -- nothing to check")
        return 0

    findings = []
    for rel in DOCS:
        if rel in HISTORICAL:
            continue
        p = ROOT / rel
        if not p.exists():
            continue
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if MARKER in line or NOISE.search(line):
                continue
            for value, figures in wanted.items():
                if re.search(rf"(?<!\d){value}(?!\d)", line):
                    findings.append((rel, n, value, figures, line.strip()))

    if not findings:
        print(f"clean: no retired value appears in {len(DOCS)} documents "
              f"({len(wanted)} retired values checked)")
        return 0

    print(f"{len(findings)} possible stale citation(s):\n")
    for rel, n, value, figures, line in findings:
        print(f"  {rel}:{n}  {value} was {', '.join(figures)}")
        print(f"      {line[:110]}")
    print("\nIf a mention is deliberately historical, add the "
          f"'{MARKER}' marker to that line or list the file in HISTORICAL.")
    return 1 if strict else 0


if __name__ == "__main__":
    raise SystemExit(main())
