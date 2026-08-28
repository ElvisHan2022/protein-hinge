#!/usr/bin/env python3
"""Scan the paper sources for anything that identifies the authors.

The submission is double-blind. A desk reject for a leaked identity costs the
whole cycle, and identity leaks are exactly the kind of thing that reads fine
to the person who wrote it -- the same silent-error shape the paper is about.
So it gets a mechanical check rather than a careful read.

    python3 scripts/check_anonymity.py            report, exit 0
    python3 scripts/check_anonymity.py --strict   exit 1 on any finding

Scans paper/ by default. Pass paths to scan something else.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# (pattern, why it identifies us). Case-insensitive.
PATTERNS: list[tuple[str, str]] = [
    (r"protein[\s_-]?hinge", "project name, public on a code host"),
    (r"biobitworks", "organisation name"),
    (r"elvis", "author name"),
    (r"byron", "author name"),
    (r"\bhail\b", "team handle"),
    (r"github\.com", "repository URL deanonymises the authors"),
    (r"zenodo", "prior self-published work identifies the author"),
    (r"hackathon", "the event narrative identifies the team"),
    (r"newinml", "venue mention inside the paper body"),
    (r"\bclaude\b|anthropic|openai|\bgpt-", "tooling attribution"),
    (r"aws\s+account|\b\d{12}\b", "cloud account identifier"),
    (r"healthomics|clinvar\s+subset\s+for\s+the\s+eight", "distinctive infra fingerprint"),
    (r"acknowledg", "acknowledgements must be empty at submission"),
    (r"\bwe thank\b", "thanks identify collaborators"),
    (r"@[\w.-]+\.(com|org|edu|net)", "email address"),
]

DEFAULT_TARGETS = ["paper"]
# Internal working documents that are never part of the submission. They may
# name the team freely; the check applies to what actually goes into the PDF.
NOT_SUBMITTED = {"paper/README.md"}
SKIP_SUFFIXES = {".pdf", ".png", ".jpg", ".aux", ".log", ".out", ".bbl", ".blg", ".synctex"}
# The bib deliberately records verification notes; identity checks still apply
# to it, but a URL to a standards body is not an identity leak.
ALLOW = re.compile(r"rfc-editor\.org|doi\.org|crossref|proceedings\.neurips\.cc|jmlr\.org")


def main() -> int:
    strict = "--strict" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    targets = args or DEFAULT_TARGETS

    files: list[Path] = []
    for t in targets:
        p = ROOT / t
        if p.is_dir():
            files += [f for f in p.rglob("*")
                      if f.is_file() and f.suffix.lower() not in SKIP_SUFFIXES]
        elif p.is_file():
            files.append(p)
    files = [f for f in files
             if f.relative_to(ROOT).as_posix() not in NOT_SUBMITTED]

    if not files:
        print(f"no files found under {targets}")
        return 1

    findings = []
    for f in sorted(files):
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for n, line in enumerate(text.splitlines(), 1):
            if ALLOW.search(line):
                continue
            for pat, why in PATTERNS:
                if re.search(pat, line, re.IGNORECASE):
                    findings.append((f.relative_to(ROOT), n, why, line.strip()[:96]))

    print(f"scanned {len(files)} file(s) under {', '.join(targets)}")
    if not findings:
        print("clean: no identifying term found")
        return 0

    print(f"\n{len(findings)} possible identity leak(s):\n")
    for rel, n, why, line in findings:
        print(f"  {rel}:{n}  [{why}]")
        print(f"      {line}")
    print("\nRemove or neutralise each before submitting. A double-blind "
          "violation can be desk-rejected.")
    return 1 if strict else 0


if __name__ == "__main__":
    raise SystemExit(main())
