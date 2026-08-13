#!/usr/bin/env python3
"""
FTO lane: node constructors for the freedom-to-operate evidence file.

This module adds NO new custody machinery. An FTO search result is a source, a
search is a derivation, a triage is a derivation that requires a named human,
and a finding is a claim. Same admission rule, same routes, same tamper test.

The one thing this module does that fcg.py does not is refuse a specific word.
See emit_finding(): FTO_OPINION is a legal conclusion and this system is not
qualified to issue one. The level exists in the enum so the code can decline it
out loud rather than by omission.

Nothing produced here is legal advice.
"""
from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fcg"))

from fcg import FCG  # noqa: E402

SCHEMA_FTO_SEARCH = "biocustody.fto.search.v1"
SCHEMA_FTO_TRIAGE = "biocustody.fto.triage.v1"
SCHEMA_FTO_FINDING = "biocustody.fto.finding.v1"

# Ordered. Each level is strictly stronger than the one before it.
FTO_LEVELS = (
    "COMMITTED",                # a search ran; its results were hashed
    "RECOMPUTED",               # the search replays to the same digest
    "SCREENED",                 # a named human triaged the results
    "CLEARANCE_SEARCH_RECORD",  # the ceiling this system may reach
    "FTO_OPINION",              # outside counsel only. never us.
)
FTO_CEILING = "CLEARANCE_SEARCH_RECORD"

LANES = {
    "D": "DATA — may we use the inputs?",
    "M": "METHOD — may we run and sell the pipeline?",
    "C": "COMPOUND — may we develop the molecule we find?",
}


# ---------------------------------------------------------------------------
# registries
# ---------------------------------------------------------------------------
# Each entry is a corpus we can query reproducibly. "reproducible" is a
# property of the endpoint, not a hope: a query with no date bound returns
# different bytes tomorrow, which is why corpus_date is hashed into every node.

REGISTRIES = {
    "clinicaltrials_gov": {
        "name": "ClinicalTrials.gov",
        "api": "https://clinicaltrials.gov/api/v2/studies",
        "lane": "C",
        "answers": "Who is already developing something for this indication, "
                   "at what phase, and did it read out?",
        "public": True,
        "auth": None,
    },
    "openfda_drug": {
        "name": "openFDA drug endpoints",
        "api": "https://api.fda.gov/drug",
        "lane": "C",
        "answers": "What is approved, under what label, with what adverse "
                   "event history.",
        "public": True,
        "auth": None,
    },
    "fda_orphan": {
        "name": "FDA Orphan Drug Product designation database",
        "api": "https://www.accessdata.fda.gov/scripts/opdlisting/oopd/",
        "lane": "C",
        "answers": "Who holds orphan designation and exclusivity for this "
                   "indication, and when does it lapse.",
        "public": True,
        "auth": None,
        "note": "No stable JSON API. Query surface is a web form; treat any "
                "capture as COMMITTED and re-verify by hand.",
        "status": "NOT_CAPTURED",
    },
    "ema_epar": {
        "name": "European Medicines Agency EPAR",
        "api": None,
        "lane": "C",
        "answers": "European authorization status and product assessment records.",
        "public": True,
        "auth": None,
        "note": "Not ingested in this MVP. Add only after the query surface, "
                "corpus date, fields, and reuse terms are documented.",
        "status": "LISTED_NOT_WIRED",
    },
    "pmda_japan": {
        "name": "Japan PMDA drug approvals",
        "api": None,
        "lane": "C",
        "answers": "Japanese approval status and product records.",
        "public": True,
        "auth": None,
        "note": "Not ingested in this MVP. Add only after the query surface, "
                "corpus date, fields, and reuse terms are documented.",
        "status": "LISTED_NOT_WIRED",
    },
    "open_targets": {
        "name": "Open Targets Platform",
        "api": "https://api.platform.opentargets.org/api/v4/graphql",
        "lane": "C",
        "answers": "Is the target–disease association supported independently "
                   "of our morphology, and what tractability does the target "
                   "have for a small molecule.",
        "public": True,
        "auth": None,
        "why_it_matters": "This is the strongest available ORTHOGONAL check. "
                          "Open Targets evidence is genetic, literature, and "
                          "pathway based — it does not come from Cell "
                          "Painting. Agreement is therefore real corroboration "
                          "rather than the same signal counted twice.",
    },
    "convoke": {
        "name": "Convoke",
        "api": None,
        "lane": "C",
        "answers": "unknown to this repo — see note",
        "public": False,
        "auth": "CONVOKE_MCP_TOKEN",
        "note": "Referenced by the partner repo as an MCP requiring "
                "CONVOKE_MCP_TOKEN. We do not hold that token and must not "
                "hold it in this repo. Credentials live in .env and are never "
                "committed. Until someone with access documents the query "
                "surface and the license terms of what it returns, Convoke is "
                "listed and NOT wired. An undocumented source cannot be "
                "admitted, because its results cannot be recomputed by anyone "
                "else.",
        "status": "LISTED_NOT_WIRED",
    },
}


def registry_status() -> List[Dict[str, Any]]:
    return [
        {
            "key": k,
            "name": v["name"],
            "lane": v["lane"],
            "public": v["public"],
            "wired": v.get("status") is None and v["api"] is not None,
            "blocker": v.get("note") if v.get("status") is not None else None,
        }
        for k, v in sorted(REGISTRIES.items())
    ]


# ---------------------------------------------------------------------------
# node constructors
# ---------------------------------------------------------------------------

def add_search(g: FCG, label: str, registry: str, query: Any,
               corpus_date: str, result_source_ids: List[str],
               result_count: int, filters: Optional[Dict[str, Any]] = None,
               lane: str = "C") -> str:
    """A named, replayable query over a named corpus.

    corpus_date is hashed into the node body on purpose. The same query run on
    two dates is two different nodes with two different ids, so a stale
    clearance cannot be silently reused.
    """
    if registry not in REGISTRIES:
        raise ValueError(f"unknown registry {registry!r}")
    if lane not in LANES:
        raise ValueError(f"unknown lane {lane!r}")
    reg = REGISTRIES[registry]
    if reg.get("status") == "LISTED_NOT_WIRED":
        raise ValueError(
            f"{reg['name']} is listed but not wired: {reg['note']} "
            "A search cannot be admitted against a corpus nobody else can query."
        )
    return g.add_derivation(
        label=label, layer=1, fn="fto_search",
        inputs=result_source_ids,
        payload={
            "schema": SCHEMA_FTO_SEARCH,
            "lane": lane,
            "lane_meaning": LANES[lane],
            "registry": registry,
            "registry_name": reg["name"],
            "endpoint": reg["api"],
            "query": query,
            "filters": filters or {},
            "corpus_date": corpus_date,
            "result_count": result_count,
            "evidence_level": "COMMITTED",
            "means": "A search ran and its results were hashed. Nobody has read them.",
        },
        params={"registry": registry, "corpus_date": corpus_date},
    )


def add_triage(g: FCG, label: str, search_ids: List[str], reviewer: str,
               reviewed_at: str, blocking: List[Dict[str, Any]],
               adjacent: List[Dict[str, Any]],
               irrelevant_count: int, rationale: str) -> str:
    """A human read the results and sorted them. Requires a named human.

    An unattributed triage is not SCREENED. If nobody's name is on it, nobody
    read it, and the level does not apply.
    """
    if not reviewer or reviewer.strip().lower() in ("", "unknown", "n/a", "tbd", "auto"):
        raise ValueError(
            "SCREENED requires a named human reviewer. An unattributed triage "
            "is not a triage."
        )
    return g.add_derivation(
        label=label, layer=2, fn="fto_triage",
        inputs=list(search_ids),
        payload={
            "schema": SCHEMA_FTO_TRIAGE,
            "reviewer": reviewer,
            "reviewed_at": reviewed_at,
            "blocking": blocking,
            "adjacent": adjacent,
            "n_blocking": len(blocking),
            "n_adjacent": len(adjacent),
            "n_irrelevant": irrelevant_count,
            "rationale": rationale,
            "evidence_level": "SCREENED",
            "not_legal_advice": True,
        },
        params={"reviewer": reviewer},
    )


def emit_finding(g: FCG, label: str, lane: str, statement: str, level: str,
                 inputs: List[str], evidence: Dict[str, Any]) -> str:
    """A layer-3 FTO finding. Capped at CLEARANCE_SEARCH_RECORD.

    The refusal below is the reason this function exists. Everything else here
    is bookkeeping.
    """
    if level not in FTO_LEVELS:
        raise ValueError(f"unknown FTO level {level!r}")
    if level == "FTO_OPINION":
        raise ValueError(
            "FTO_OPINION cannot be emitted by this system.\n"
            "A freedom-to-operate opinion is a legal conclusion issued by "
            "qualified patent counsel who signs their name to it. This "
            "repository produces the reproducible search record that counsel "
            "works from. Labelling that record an opinion would misrepresent "
            "what it is to whoever relies on it next.\n"
            f"Highest level available here: {FTO_CEILING}."
        )
    if FTO_LEVELS.index(level) > FTO_LEVELS.index(FTO_CEILING):
        raise ValueError(f"{level} exceeds the FTO ceiling {FTO_CEILING}")

    ev = dict(evidence)
    ev.update({
        "schema": SCHEMA_FTO_FINDING,
        "lane": lane,
        "lane_meaning": LANES.get(lane, lane),
        "fto_level": level,
        "fto_ceiling": FTO_CEILING,
        "disclaimer": ("Not legal advice. This is a reproducible search record, "
                       "not a freedom-to-operate opinion. No one on this project "
                       "is qualified to issue one."),
    })
    # Reuses fcg.add_claim, which independently refuses AUTHENTICATED/VALIDATED.
    return g.add_claim(
        label=label, statement=statement, level="COMMITTED",
        inputs=inputs, evidence=ev, claim_ceiling=FTO_CEILING,
    )


if __name__ == "__main__":
    print("FTO registries")
    print("-" * 66)
    for r in registry_status():
        mark = "wired" if r["wired"] else "NOT WIRED"
        print(f"  [{r['lane']}] {r['name']:<44} {mark}")
        if r["blocker"]:
            print(f"        reason: {r['blocker'][:200]}")
    print()
    print("Ceiling check")
    print("-" * 66)
    try:
        emit_finding(None, "x", "C", "y", "FTO_OPINION", [], {})
    except ValueError as e:
        print("  refused FTO_OPINION:")
        for line in str(e).split("\n"):
            print(f"    {line}")
