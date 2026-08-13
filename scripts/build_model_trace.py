#!/usr/bin/env python3
"""Build model/evidence trace assets for the dashboard."""
from __future__ import annotations

import hashlib
import json
import subprocess
import urllib.request
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "model_trace"
SITE_ASSETS = ROOT / "site" / "assets"
FIGURES = ROOT / "figures"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def try_url(url: str) -> dict:
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        return {"status": "unavailable", "reason": f"{type(exc).__name__}: {exc}"}


def ollama_inventory() -> list[dict]:
    try:
        proc = subprocess.run(["ollama", "list"], text=True, capture_output=True, check=True, timeout=10)
    except Exception as exc:
        return [{"model": "ollama", "status": "unavailable", "reason": f"{type(exc).__name__}: {exc}"}]
    rows = []
    for line in proc.stdout.splitlines()[1:]:
        parts = line.split()
        if len(parts) < 3:
            continue
        size = " ".join(parts[2:4]) if len(parts) >= 4 and parts[3] in {"MB", "GB"} else parts[2]
        rows.append({
            "model": parts[0],
            "family": "local_ollama",
            "size": size,
            "status": "installed_not_invoked_for_science",
            "trace_role": "candidate local reviewer; no scientific datum generated",
        })
    return rows


def model_size_bucket(model: str) -> str:
    for token in (":0.5b", ":1b", ":1.5b", ":1.7b", ":3b", ":7b", ":14b"):
        if token in model.lower():
            return token.replace(":", "").upper()
    return "API"


def build_null_figure(evaluation: dict) -> None:
    observed = [
        evaluation["reciprocal_rank"],
        1.0 if evaluation["hits_at_10"] else 0.0,
    ]
    null = [
        evaluation["shuffled_mean_reciprocal_rank"],
        evaluation["shuffled_hits_at_10_rate"],
    ]
    labels = ["Reciprocal rank", "Hits@10 rate"]
    x = range(len(labels))
    plt.figure(figsize=(7.4, 4.2), dpi=180)
    plt.bar([i - 0.18 for i in x], observed, width=0.36, label="Observed known pair", color="#42c2a7")
    plt.bar([i + 0.18 for i in x], null, width=0.36, label="Shuffle null", color="#e3b34f")
    plt.xticks(list(x), labels)
    plt.ylabel("score")
    plt.ylim(0, max(max(observed), max(null)) * 1.25)
    plt.title("Known-pair benchmark vs shuffle null")
    plt.legend(frameon=False)
    plt.tight_layout()
    FIGURES.mkdir(exist_ok=True)
    SITE_ASSETS.mkdir(parents=True, exist_ok=True)
    png = FIGURES / "null_hypothesis_comparison.png"
    plt.savefig(png, bbox_inches="tight")
    plt.close()
    (SITE_ASSETS / "null_hypothesis_comparison.png").write_bytes(png.read_bytes())


def main() -> None:
    OUT.mkdir(exist_ok=True)
    SITE_ASSETS.mkdir(parents=True, exist_ok=True)
    evaluation = read_json(ROOT / "data" / "partner" / "evaluation.json")
    fanout = read_json(ROOT / "fco" / "agent_fanout" / "20260813Tfanout-elvis" / "manifest.fco.json")
    fco_manifest_path = Path("/Users/byron/projects/active/fractal-custody-objects/PUBLIC_CUSTODY_MANIFEST.json")
    seedgraph_readme = Path("/Users/byron/projects/active/seedgraph/README.md")
    hackathon_context_path = OUT / "aws_hackathon_context.json"

    ollarma = try_url("http://127.0.0.1:8484/startup/readiness")
    local_models = ollama_inventory()
    openai_model = {
        "model": fanout.get("model"),
        "family": "openai_api",
        "size": "API",
        "status": "invoked_for_demo_subagents",
        "trace_role": "generated bounded navigation/update summaries as FCOs",
        "fco_count": fanout.get("agent_fco_count"),
        "model_fco_id": fanout.get("model_fco_id"),
        "integration_fco_id": fanout.get("integration_fco_id"),
    }
    trace = {
        "schema": "protein_hinge.model_trace.v1",
        "claim_boundary": "Model outputs are trace/navigation evidence only; models did not create scientific input data.",
        "watchtower_search": {
            "checked": True,
            "status": "degraded",
            "reason": "semantic embedding timeout; local file evidence used for fast-track integration",
        },
        "ollarma_readiness": ollarma,
        "models": [openai_model] + local_models,
        "source_projects": {
            "seedgraph": {
                "path": str(seedgraph_readme.parent),
                "readme_sha256": sha256_file(seedgraph_readme) if seedgraph_readme.exists() else None,
                "status": "local_reference_checked" if seedgraph_readme.exists() else "missing",
            },
            "fractal_custody_objects": {
                "path": str(fco_manifest_path.parent),
                "public_manifest_sha256": sha256_file(fco_manifest_path) if fco_manifest_path.exists() else None,
                "status": "local_reference_checked" if fco_manifest_path.exists() else "missing",
            },
            "gettingsciencedone": {
                "path": "/Users/byron/projects/active/gettingsciencedone",
                "null_script": "/Users/byron/projects/active/gettingsciencedone/scripts/null_hypothesis_analysis.py",
                "status": "local_reference_checked",
            },
        },
        "hackathon_context": read_json(hackathon_context_path) if hackathon_context_path.exists() else None,
        "null_hypothesis": {
            "dataset": "data/partner/evaluation.json",
            "dataset_sha256": sha256_file(ROOT / "data" / "partner" / "evaluation.json"),
            "shuffle_iterations": evaluation["shuffle_iterations"],
            "shuffle_seed": evaluation["shuffle_seed"],
            "known_pair_rank": evaluation["known_pair_rank"],
            "observed_reciprocal_rank": evaluation["reciprocal_rank"],
            "shuffle_mean_reciprocal_rank": evaluation["shuffled_mean_reciprocal_rank"],
            "reciprocal_rank_enrichment_vs_shuffle": evaluation["reciprocal_rank_enrichment_vs_shuffle"],
            "observed_hits_at_10": evaluation["hits_at_10"],
            "shuffle_hits_at_10_rate": evaluation["shuffled_hits_at_10_rate"],
            "plain_english": (
                "The known reference pair did not beat the shuffle null in this tiny benchmark. "
                "That is a useful negative result and keeps the claim ceiling conservative."
            ),
        },
        "figures": {
            "null_comparison": "figures/null_hypothesis_comparison.png",
            "dashboard_copy": "site/assets/null_hypothesis_comparison.png",
        },
    }
    build_null_figure(evaluation)
    (OUT / "model_trace.json").write_text(json.dumps(trace, indent=2, sort_keys=True) + "\n")
    (SITE_ASSETS / "model_trace.json").write_text(json.dumps(trace, indent=2, sort_keys=True) + "\n")
    if hackathon_context_path.exists():
        (SITE_ASSETS / "aws_hackathon_context.json").write_text(hackathon_context_path.read_text())
    print(f"wrote {OUT.relative_to(ROOT) / 'model_trace.json'}")
    print("wrote figures/null_hypothesis_comparison.png")


if __name__ == "__main__":
    main()
