#!/usr/bin/env python3
"""
Build the Protein Hinge cell-perturbation scientific figure.

Inputs are the small public partner artifacts that are already named and
hash-pinned in the FCG store. This script verifies their hashes before plotting
and writes a provenance sidecar next to the figure.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "partner"
FIGURES = ROOT / "figures"
SITE_ASSETS = ROOT / "site" / "assets"

EXPECTED = {
    "candidate_ranking.csv": "e93d3ce7526049c8904e36e6e1aeefc2558c38b3032c8c348342390d8cf30b51",
    "state_model.json": "4028c343675f298ba3c91171b94a9d9741a5a52e226119b3080ae7390408a18a",
    "perturbation_state.json": "c6fa95aaf2094767f613f6900f737a6cadc5e0b996b46ea83a3cfe7516bb1bf7",
    "evaluation.json": "ede568677be5d45412f359153ebd60ada87b23ec93db6a33f9e836bce1bea62f",
}

SOURCES = {
    "candidate_ranking.csv": "https://raw.githubusercontent.com/biobitworks/aws-biopharma/main/data/magicstudiobox/runs/primary/candidate_ranking.csv",
    "state_model.json": "https://raw.githubusercontent.com/biobitworks/aws-biopharma/main/data/magicstudiobox/runs/primary/state_model.json",
    "perturbation_state.json": "https://raw.githubusercontent.com/biobitworks/aws-biopharma/main/data/magicstudiobox/runs/primary/perturbation_state.json",
    "evaluation.json": "https://raw.githubusercontent.com/biobitworks/aws-biopharma/main/data/magicstudiobox/runs/primary/evaluation.json",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def require_inputs() -> dict[str, str]:
    observed = {}
    missing = []
    mismatch = []
    for name, expected in EXPECTED.items():
        path = DATA / name
        if not path.exists():
            missing.append(name)
            continue
        got = sha256(path)
        observed[name] = got
        if got != expected:
            mismatch.append((name, expected, got))
    if missing:
        raise SystemExit(
            "missing input(s): "
            + ", ".join(missing)
            + "\nRun the curl commands in docs/MVP_STATUS.md to refresh data/partner/."
        )
    if mismatch:
        lines = ["hash mismatch; refusing to plot unpinned data:"]
        for name, expected, got in mismatch:
            lines.append(f"  {name}: expected {expected}, got {got}")
        raise SystemExit("\n".join(lines))
    return observed


def load_json(name: str):
    with (DATA / name).open() as fh:
        return json.load(fh)


def short(text: str, width: int = 20) -> str:
    return text if len(text) <= width else text[: width - 1] + "..."


def main() -> None:
    hashes = require_inputs()
    FIGURES.mkdir(parents=True, exist_ok=True)
    SITE_ASSETS.mkdir(parents=True, exist_ok=True)

    rank = pd.read_csv(DATA / "candidate_ranking.csv")
    state = load_json("state_model.json")
    perturb = load_json("perturbation_state.json")
    evaln = load_json("evaluation.json")

    rank["rank"] = np.arange(1, len(rank) + 1)
    for col in [
        "candidate_distance",
        "candidate_distance2",
        "perturbation_distance",
        "restoration_score",
        "distance_ratio",
    ]:
        rank[col] = pd.to_numeric(rank[col])

    top = rank.iloc[0]
    known = rank[rank["target_match"].astype(bool)].head(1)
    known_row = known.iloc[0] if len(known) else None
    pert_d = float(rank["perturbation_distance"].iloc[0])
    pert_d2 = float(state["state_decision"]["distance2"])
    threshold2 = float(state["state_decision"]["threshold2"])
    threshold = threshold2 ** 0.5
    selected_gene = perturb.get("selected_gene", "selected perturbation")
    selected_id = perturb.get("selected_perturbation_id", selected_gene)

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "axes.titlesize": 10,
            "axes.labelsize": 9,
            "figure.dpi": 160,
            "savefig.dpi": 240,
        }
    )

    fig = plt.figure(figsize=(12.5, 8.0), constrained_layout=True)
    gs = fig.add_gridspec(2, 2, height_ratios=[1.0, 1.05])
    ax0 = fig.add_subplot(gs[0, 0])
    ax1 = fig.add_subplot(gs[0, 1])
    ax2 = fig.add_subplot(gs[1, 0])
    ax3 = fig.add_subplot(gs[1, 1])

    # Panel A: distance threshold and selected states.
    bar_labels = ["q95 reference\nthreshold", f"{selected_gene}\nperturbed", short(top["pert_iname"])]
    bar_vals = [threshold2, pert_d2, float(top["candidate_distance2"])]
    colors = ["#8d99a6", "#c55a3d", "#2f7f75"]
    if known_row is not None:
        bar_labels.append(short(known_row["pert_iname"]))
        bar_vals.append(float(known_row["candidate_distance2"]))
        colors.append("#b98b2f")
    x = np.arange(len(bar_vals))
    ax0.bar(x, bar_vals, color=colors, edgecolor="#263238", linewidth=0.8)
    ax0.axhline(threshold2, color="#59636f", linestyle="--", linewidth=1.2)
    for xi, yi in zip(x, bar_vals):
        ax0.text(xi, yi + max(bar_vals) * 0.03, f"{yi:.1f}", ha="center", va="bottom", fontsize=8)
    ax0.set_xticks(x, bar_labels)
    ax0.set_ylabel("Squared distance to reference (D^2)")
    ax0.set_title("A. Selected perturbation exceeds the reference threshold")
    ax0.text(
        0.02,
        0.86,
        f"state rule: D^2 > q95 threshold ({threshold2:.1f})",
        transform=ax0.transAxes,
        ha="left",
        va="top",
        color="#4f5965",
        fontsize=8,
        bbox={"boxstyle": "round,pad=0.25", "facecolor": "white", "edgecolor": "none", "alpha": 0.8},
    )

    # Panel B: top ranked candidate restoration scores.
    topn = rank.head(15).iloc[::-1]
    bar_colors = ["#2f7f75" if not bool(v) else "#b98b2f" for v in topn["target_match"]]
    ax1.barh(topn["pert_iname"], topn["restoration_score"], color=bar_colors, edgecolor="#263238", linewidth=0.5)
    ax1.set_xlabel("Restoration score = 1 - D(candidate, ref) / D(perturbation, ref)")
    ax1.set_title("B. Top candidate profiles move toward the reference state")
    ax1.set_xlim(0, max(0.55, float(topn["restoration_score"].max()) * 1.12))
    ax1.grid(axis="x", color="#d9dee3", linewidth=0.6)
    ax1.set_axisbelow(True)

    # Panel C: all 50 candidates in distance-score space.
    matched = rank["target_match"].astype(bool)
    ax2.scatter(
        rank.loc[~matched, "candidate_distance"],
        rank.loc[~matched, "restoration_score"],
        s=34,
        color="#527aa3",
        alpha=0.78,
        edgecolor="white",
        linewidth=0.5,
        label="candidate",
    )
    if matched.any():
        ax2.scatter(
            rank.loc[matched, "candidate_distance"],
            rank.loc[matched, "restoration_score"],
            s=72,
            marker="D",
            color="#b98b2f",
            edgecolor="#263238",
            linewidth=0.7,
            label="target match",
        )
    ax2.axvline(pert_d, color="#c55a3d", linestyle="--", linewidth=1.1, label=f"{selected_gene} perturbation")
    ax2.axvline(threshold, color="#59636f", linestyle=":", linewidth=1.1, label="q95 threshold")
    ax2.set_xlabel("Distance to reference phenotype (D)")
    ax2.set_ylabel("Restoration score")
    ax2.set_title("C. Distance-domain restoration benchmark, n=50")
    ax2.legend(frameon=False, fontsize=8, loc="upper right")
    ax2.grid(color="#e5e9ed", linewidth=0.6)
    ax2.set_axisbelow(True)

    # Panel D: concise provenance and interpretation.
    ax3.axis("off")
    summary = [
        ("Dataset", "CPJUMP1 processed subset / Cell Painting profiles"),
        ("Reference state", f"{state['reference_state']['replicate_count']} control replicates"),
        ("Selected perturbation", selected_id),
        ("Candidate count", str(len(rank))),
        ("Top candidate", f"{top['pert_iname']} ({top['target']})"),
        ("Top score", f"{top['restoration_score']:.3f}"),
        ("Known-pair rank", str(evaln["known_pair_rank"])),
        ("Claim ceiling", evaln["claim_ceiling"]),
    ]
    y = 0.96
    ax3.text(0.0, y, "D. Provenance and interpretation", fontsize=10, fontweight="bold", va="top")
    y -= 0.09
    for k, v in summary:
        ax3.text(0.0, y, k, color="#4f5965", fontweight="bold", va="top")
        ax3.text(0.36, y, textwrap.fill(v, width=42), va="top")
        y -= 0.075
    y -= 0.02
    note = (
        "Interpretation: candidates are ranked by return toward the reference "
        "phenotype in a processed morphology distance space. This is predicted "
        "counter-perturbation, not measured rescue or therapeutic efficacy."
    )
    ax3.text(0.0, y, textwrap.fill(note, width=76), va="top")
    y -= 0.22
    hash_lines = [
        f"candidate_ranking.csv sha256:{hashes['candidate_ranking.csv'][:12]}...",
        f"state_model.json sha256:{hashes['state_model.json'][:12]}...",
        f"perturbation_state.json sha256:{hashes['perturbation_state.json'][:12]}...",
    ]
    ax3.text(0.0, y, "Pinned inputs", color="#4f5965", fontweight="bold", va="top")
    ax3.text(0.36, y, "\n".join(hash_lines), family="DejaVu Sans Mono", fontsize=8, va="top")

    fig.suptitle(
        "Protein Hinge: CPJUMP1 cell perturbation restoration figure",
        fontsize=13,
        fontweight="bold",
    )

    png = FIGURES / "cell_perturbation_restoration.png"
    svg = FIGURES / "cell_perturbation_restoration.svg"
    pdf = FIGURES / "cell_perturbation_restoration.pdf"
    fig.savefig(png, bbox_inches="tight")
    fig.savefig(svg, bbox_inches="tight")
    fig.savefig(pdf, bbox_inches="tight")
    plt.close(fig)

    shutil.copy2(png, SITE_ASSETS / png.name)

    sidecar = {
        "schema": "protein_hinge.figure_provenance.v1",
        "figure": {
            "title": "Protein Hinge: CPJUMP1 cell perturbation restoration figure",
            "files": {
                "png": str(png.relative_to(ROOT)),
                "svg": str(svg.relative_to(ROOT)),
                "pdf": str(pdf.relative_to(ROOT)),
                "dashboard_copy": str((SITE_ASSETS / png.name).relative_to(ROOT)),
            },
        },
        "inputs": [
            {
                "file": f"data/partner/{name}",
                "source": SOURCES[name],
                "sha256": "sha256:" + hashes[name],
            }
            for name in sorted(hashes)
        ],
        "calculation": {
            "script": "scripts/make_cell_perturbation_figure.py",
            "selected_perturbation": selected_id,
            "candidate_count": int(len(rank)),
            "restoration_score": "1 - candidate_distance / perturbation_distance",
            "distance_threshold": "state_model.state_decision.threshold2, empirical q95 in squared-distance space",
            "claim_ceiling": evaln["claim_ceiling"],
        },
        "caveat": "Predicted counter-perturbation in processed Cell Painting morphology space; not measured rescue or therapeutic efficacy.",
    }
    with (FIGURES / "cell_perturbation_restoration.provenance.json").open("w") as fh:
        json.dump(sidecar, fh, indent=2, sort_keys=True)

    print(f"wrote {png.relative_to(ROOT)}")
    print(f"wrote {svg.relative_to(ROOT)}")
    print(f"wrote {pdf.relative_to(ROOT)}")
    print(f"wrote {FIGURES.relative_to(ROOT) / 'cell_perturbation_restoration.provenance.json'}")


if __name__ == "__main__":
    main()
