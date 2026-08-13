#!/usr/bin/env python3
"""Closed target vocabulary reconciliation for the GAP lane."""
from __future__ import annotations

import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
ALIAS_TABLE = HERE / "alias_table.json"


def _clean(value: str) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def load_aliases(path: Path = ALIAS_TABLE) -> dict[str, str]:
    data = json.loads(path.read_text())
    return {k: v for k, v in data.get("aliases", {}).items()}


def reconcile(open_targets_symbol: str, program_target: str, aliases: dict[str, str] | None = None) -> dict[str, str]:
    """Return EXACT, MAPPED, or UNRESOLVED.

    No fuzzy matching and no model repair. If the closed table cannot reconcile
    a name, the caller must abstain and count the row.
    """
    aliases = aliases or load_aliases()
    ot = str(open_targets_symbol or "").strip()
    raw = str(program_target or "").strip()
    if _clean(ot) == _clean(raw):
        return {"outcome": "EXACT", "target_symbol": ot, "alias_used": ""}
    mapped = aliases.get(raw)
    if mapped and _clean(mapped) == _clean(ot):
        return {"outcome": "MAPPED", "target_symbol": ot, "alias_used": raw}
    return {"outcome": "UNRESOLVED", "target_symbol": ot, "alias_used": raw}


def _self_test() -> None:
    cases = [
        ("TTR", "TTR", "EXACT"),
        ("SMN1", "SMN1", "EXACT"),
        ("PARP1", "PARP1", "EXACT"),
        ("PDCD1", "PD-1", "MAPPED"),
        ("PDCD1", "PD1", "MAPPED"),
        ("CFB", "Factor B", "MAPPED"),
        ("TAZ", "TAZ", "EXACT"),
        ("TAZ", "tafazzin", "UNRESOLVED"),
        ("CFB", "factor c", "UNRESOLVED"),
        ("PARP1", "", "UNRESOLVED"),
    ]
    for ot, raw, want in cases:
        got = reconcile(ot, raw)["outcome"]
        if got != want:
            raise SystemExit(f"{ot!r} x {raw!r}: got {got}, want {want}")
    print("normalize self-test OK")


if __name__ == "__main__":
    _self_test()
