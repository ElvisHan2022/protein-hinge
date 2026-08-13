#!/usr/bin/env python3
"""Build Cytoscape and static graph artifacts from the latest fan-out FCOs."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx


ROOT = Path(__file__).resolve().parents[1]
FCO_ROOT = ROOT / "fco" / "agent_fanout"
SITE_ASSETS = ROOT / "site" / "assets"
FIGURES = ROOT / "figures"


def load_latest_dir() -> Path:
    latest = json.loads((FCO_ROOT / "latest.json").read_text())
    return ROOT / latest["path"]


def short_hash(value: str) -> str:
    return value.replace("sha256:", "")[:12]


def main() -> None:
    run_dir = load_latest_dir()
    manifest = json.loads((run_dir / "manifest.fco.json").read_text())
    fcos = [
        json.loads(path.read_text())
        for path in sorted(run_dir.glob("*.fco.json"))
        if path.name != "manifest.fco.json"
    ]
    by_id = {fco["fco_id"]: fco for fco in fcos if fco.get("fco_id")}

    nodes = [
        {"data": {"id": "objective", "label": "objective", "kind": "objective"}},
        {"data": {"id": "inputs", "label": "hashed inputs", "kind": "input"}},
        {"data": {"id": "root", "label": "fan-out root\\n" + short_hash(manifest["merkle_root"]), "kind": "root"}},
        {"data": {"id": "dashboard", "label": "dashboard update", "kind": "update"}},
        {"data": {"id": "docs", "label": "docs/script update", "kind": "update"}},
    ]
    edges = [
        {"data": {"id": "objective-inputs", "source": "objective", "target": "inputs", "label": "scopes"}},
    ]

    for fco in fcos:
        fco_type = fco.get("fco_type", "fco")
        if fco_type == "openai_subagent_fanout":
            aid = fco["agent"]["agent_id"]
            parsed = fco.get("output", {}).get("json") or {}
            update = parsed.get("proposed_update") if isinstance(parsed, dict) else None
            label = f"{aid}\\n{short_hash(fco['fco_id'])}"
            nodes.append(
                {
                    "data": {
                        "id": aid,
                        "label": label,
                        "kind": "agent_fco",
                        "fco_id": fco["fco_id"],
                        "role": fco["agent"]["role"],
                        "summary": parsed.get("summary") if isinstance(parsed, dict) else fco.get("output", {}).get("text", "")[:160],
                        "proposed_update": update or fco["agent"]["update_target"],
                    }
                }
            )
            edges.append({"data": {"id": f"inputs-{aid}", "source": "inputs", "target": aid, "label": "read"}})
            target = "dashboard" if "dashboard" in fco["agent"]["update_target"] or aid in {"navigator", "fco_mapper", "elvis_integrator"} else "docs"
            edges.append({"data": {"id": f"{aid}-{target}", "source": aid, "target": target, "label": "proposes"}})
        elif fco_type == "openai_model":
            nodes.append({
                "data": {
                    "id": "model",
                    "label": "model\\n" + short_hash(fco["fco_id"]),
                    "kind": "model_fco",
                    "fco_id": fco["fco_id"],
                    "role": fco.get("model", {}).get("model_requested", "openai model"),
                    "summary": "OpenAI model object used by the run.",
                }
            })
        elif fco_type == "fanout_integration":
            nodes.append({
                "data": {
                    "id": "integration",
                    "label": "integration\\n" + short_hash(fco["fco_id"]),
                    "kind": "integration_fco",
                    "fco_id": fco["fco_id"],
                    "role": "Fan-out integration object",
                    "summary": "Links model, agent objects, dashboard, database projection, and claim ceiling.",
                }
            })

    integration = next((f for f in fcos if f.get("fco_type") == "fanout_integration"), None)
    if integration:
        edges.append({"data": {"id": "inputs-integration", "source": "inputs", "target": "integration", "label": "binds"}})
        if integration.get("model_object") in by_id:
            edges.append({"data": {"id": "model-integration", "source": "model", "target": "integration", "label": "uses"}})
        for aid, fco in [
            (f.get("agent", {}).get("agent_id"), f)
            for f in fcos
            if f.get("fco_type") == "openai_subagent_fanout"
        ]:
            if aid:
                edges.append({"data": {"id": f"{aid}-integration", "source": aid, "target": "integration", "label": "integrates"}})
        edges.append({"data": {"id": "integration-root", "source": "integration", "target": "root", "label": "rooted"}})

    elements = {"nodes": nodes, "edges": edges}
    SITE_ASSETS.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    (SITE_ASSETS / "agent_fanout_graph.cyjs").write_text(json.dumps({"elements": elements, "manifest": manifest}, indent=2, sort_keys=True) + "\n")

    graph = nx.DiGraph()
    for n in nodes:
        graph.add_node(n["data"]["id"], label=n["data"]["label"], kind=n["data"]["kind"])
    for e in edges:
        graph.add_edge(e["data"]["source"], e["data"]["target"], label=e["data"]["label"])

    pos = nx.spring_layout(graph, seed=260813, k=1.1)
    color_map = {
        "objective": "#8d99a6",
        "input": "#527aa3",
        "agent_fco": "#2f7f75",
        "model_fco": "#527aa3",
        "integration_fco": "#c55a3d",
        "root": "#c55a3d",
        "update": "#b98b2f",
    }
    colors = [color_map.get(graph.nodes[n].get("kind"), "#8d99a6") for n in graph.nodes]
    plt.figure(figsize=(10, 6), dpi=160)
    nx.draw_networkx_edges(graph, pos, arrows=True, arrowstyle="-|>", width=1.2, edge_color="#83909c")
    nx.draw_networkx_nodes(graph, pos, node_size=2400, node_color=colors, edgecolors="#263238", linewidths=0.8)
    nx.draw_networkx_labels(graph, pos, labels={n: graph.nodes[n]["label"] for n in graph.nodes}, font_size=7)
    nx.draw_networkx_edge_labels(graph, pos, edge_labels={(u, v): d["label"] for u, v, d in graph.edges(data=True)}, font_size=6)
    plt.title("Protein Hinge OpenAI fan-out: each subagent is an FCO", fontsize=12, fontweight="bold")
    plt.axis("off")
    png = FIGURES / "agent_fanout_fco_graph.png"
    plt.savefig(png, bbox_inches="tight")
    plt.close()
    print(f"wrote {SITE_ASSETS.relative_to(ROOT) / 'agent_fanout_graph.cyjs'}")
    print(f"wrote {png.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
