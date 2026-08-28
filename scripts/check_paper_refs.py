#!/usr/bin/env python3
"""Check the paper resolves: every macro defined, every citation in the bib.

LaTeX fails late and loudly on an undefined macro, but a *stale* macro -- one
defined with an old value, or cited but silently empty -- fails quietly. Since
this paper's whole argument is about mechanical checks, it gets one.

    python3 scripts/check_paper_refs.py [--strict]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "paper" / "main.tex"
GEN = ROOT / "paper" / "generated" / "results.tex"
BIB = ROOT / "paper" / "references.bib"

BS = chr(92)


def main() -> int:
    strict = "--strict" in sys.argv
    problems = 0

    tex = MAIN.read_text(encoding="utf-8")
    gen = GEN.read_text(encoding="utf-8")
    bib = BIB.read_text(encoding="utf-8")

    defined = set(re.findall(re.escape(BS) + r"newcommand\{" + re.escape(BS) + r"(\w+)\}", gen))
    # every backslash-command used in the body, minus LaTeX's own
    used_all = set(re.findall(re.escape(BS) + r"([A-Za-z]+)", tex))
    used = {u for u in used_all if u in defined or u.startswith(("GOne", "GTwo", "Corpus", "Seq"))}

    missing = sorted(used - defined)
    unused = sorted(defined - used)
    print(f"macros    defined={len(defined)} used={len(used)}")
    if missing:
        print(f"  MISSING (used in main.tex, not generated): {missing}")
        problems += len(missing)
    if unused:
        print(f"  unused (generated, not cited -- harmless): {len(unused)}")

    keys = set()
    for group in re.findall(re.escape(BS) + r"cite[pt]?\{([^}]+)\}", tex):
        keys |= {k.strip() for k in group.split(",")}
    bibkeys = set(re.findall(r"@\w+\{([^,]+),", bib))
    nobib = sorted(keys - bibkeys)
    print(f"citations cited={len(keys)} in-bib={len(bibkeys)}")
    if nobib:
        print(f"  MISSING from references.bib: {nobib}")
        problems += len(nobib)
    orphan = sorted(bibkeys - keys)
    if orphan:
        print(f"  in bib but never cited: {orphan}")

    unver = re.findall(r"@\w+\{([^,]+),(?:[^@]*?)UNVERIFIED", bib, re.S)
    if unver:
        print(f"  UNVERIFIED citations needing manual confirmation: {sorted(set(unver))}")

    if BS + "usepackage[final]" in tex or "[final]{neurips" in tex:
        print("  ANONYMITY: neurips style is in [final] mode -- this de-anonymises the paper")
        problems += 1

    print("\n" + ("clean" if problems == 0 else f"{problems} problem(s)"))
    return 1 if (problems and strict) else 0


if __name__ == "__main__":
    raise SystemExit(main())
