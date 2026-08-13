#!/usr/bin/env python3
"""
Run a bounded OpenAI fan-out and store each subagent response as its own FCO.

Secrets are read from .env or an explicit --env-file and are never written to
the output FCOs. The script uses the HTTPS API directly so it can run in a
minimal Python environment without the openai package.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV_CANDIDATES = [
    ROOT / ".env",
    Path("/Users/byron/projects/active/biocustody/.env"),
]
OUT_ROOT = ROOT / "fco" / "agent_fanout"
SITE_ASSETS = ROOT / "site" / "assets"


AGENTS = [
    {
        "agent_id": "navigator",
        "role": "Evidence navigator",
        "objective": "Trace how a viewer should navigate from scientific result to custody receipt.",
        "update_target": "dashboard navigation and video script",
    },
    {
        "agent_id": "figure_auditor",
        "role": "Scientific figure auditor",
        "objective": "Review whether the CPJUMP1 restoration figure is honest about data, distance, and claim ceiling.",
        "update_target": "figure caveats and pitch claims",
    },
    {
        "agent_id": "fco_mapper",
        "role": "FCO graph mapper",
        "objective": "Map the fan-out itself as content-addressed FCOs and describe what each node updates.",
        "update_target": "agent graph and provenance model",
    },
    {
        "agent_id": "elvis_integrator",
        "role": "Elvis component integrator",
        "objective": "Review the prescripted rare-disease repurposing demo and the live ClinicalTrials probe against the claim ceiling.",
        "update_target": "ELVIS dashboard component and video script",
    },
    {
        "agent_id": "environment_packager",
        "role": "Environment packager",
        "objective": "Summarize the Python and npm packages needed to reproduce the demo locally.",
        "update_target": "requirements and package metadata",
    },
]


def canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def load_env_file(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for line in path.read_text(errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        val = val.strip().strip('"').strip("'")
        env[key.strip()] = val
    return env


def resolve_env(explicit: str | None) -> tuple[dict[str, str], str]:
    merged = dict(os.environ)
    candidates = [Path(explicit)] if explicit else DEFAULT_ENV_CANDIDATES
    for path in candidates:
        env = load_env_file(path)
        if env:
            merged.update({k: v for k, v in env.items() if v})
            if merged.get("OPENAI_API_KEY") or merged.get("OPENAPI_KEY"):
                return merged, str(path)
    return merged, "process-environment"


def extract_output_text(resp: dict[str, Any]) -> str:
    if isinstance(resp.get("output_text"), str):
        return resp["output_text"]
    chunks: list[str] = []
    for item in resp.get("output", []) or []:
        for part in item.get("content", []) or []:
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                chunks.append(part["text"])
    return "\n".join(chunks).strip()


def try_parse_json(text: str) -> Any:
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


def call_openai(api_key: str, model: str, agent: dict[str, str], run_id: str) -> dict[str, Any]:
    prompt = {
        "context": "Protein Hinge is a local MVP dashboard for a CPJUMP1 processed cell-perturbation restoration figure and a hash-pinned custody/FTO ledger.",
        "agent_id": agent["agent_id"],
        "role": agent["role"],
        "objective": agent["objective"],
        "update_target": agent["update_target"],
        "required_response_shape": {
            "summary": "one sentence",
            "navigation_path": ["ordered dashboard or repo locations"],
            "proposed_update": "one concrete demo update this agent would make",
            "evidence_boundary": "what this agent cannot claim",
            "fco_note": "how this fan-out receipt should be represented as an FCO",
        },
    }
    body = {
        "model": model,
        "input": [
            {
                "role": "system",
                "content": (
                    "You are a bounded research/demo subagent. Return compact JSON only. "
                    "Keep claims conservative. Do not request or reveal secrets."
                ),
            },
            {"role": "user", "content": json.dumps(prompt, sort_keys=True)},
        ],
        "max_output_tokens": 500,
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60, context=ssl.create_default_context()) as r:
        resp = json.loads(r.read().decode("utf-8"))
    text = extract_output_text(resp)
    parsed = try_parse_json(text)
    return {
        "request_prompt": prompt,
        "response_id": resp.get("id"),
        "response_model": resp.get("model", model),
        "output_text": text,
        "output_json": parsed,
        "api_status": "ok",
        "run_id": run_id,
    }


def build_fco(
    *,
    run_id: str,
    agent: dict[str, str],
    model: str,
    env_source: str,
    response: dict[str, Any],
    input_hashes: dict[str, str],
) -> dict[str, Any]:
    created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    provisional = {
        "schema": "protein_hinge.fco.openai_subagent.v1",
        "fco_type": "openai_subagent_fanout",
        "run_id": run_id,
        "agent": agent,
        "api": {
            "provider": "openai",
            "model_requested": model,
            "model_returned": response.get("response_model"),
            "response_id": response.get("response_id"),
            "status": response.get("api_status"),
        },
        "secret_policy": {
            "env_source": env_source,
            "api_key_committed": False,
            "api_key_hash_committed": False,
        },
        "inputs": input_hashes,
        "prompt_sha256": sha256_bytes(canonical(response.get("request_prompt", {}))),
        "output": {
            "text": response.get("output_text", ""),
            "json": response.get("output_json"),
        },
        "custody": {
            "created_at": created_at,
            "calculation_version": "scripts/run_openai_fanout.py:v2",
        },
    }
    fco_hash = sha256_bytes(canonical(provisional))
    return {
        **provisional,
        "fco_id": fco_hash,
        "content_digest": fco_hash,
    }


def write_fco(path: Path, fco: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(fco, indent=2, sort_keys=True, ensure_ascii=False) + "\n")


def build_model_fco(
    *,
    run_id: str,
    model: str,
    env_source: str,
    response_models: list[str],
    input_hashes: dict[str, str],
) -> dict[str, Any]:
    provisional = {
        "schema": "protein_hinge.fco.openai_model.v1",
        "fco_type": "openai_model",
        "run_id": run_id,
        "model": {
            "provider": "openai",
            "model_requested": model,
            "model_returned_values": sorted(set(x for x in response_models if x)),
        },
        "secret_policy": {
            "env_source": env_source,
            "api_key_committed": False,
            "api_key_hash_committed": False,
        },
        "inputs": input_hashes,
        "custody": {
            "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "calculation_version": "scripts/run_openai_fanout.py:v2",
        },
    }
    fco_hash = sha256_bytes(canonical(provisional))
    return {**provisional, "fco_id": fco_hash, "content_digest": fco_hash}


def build_integration_fco(
    *,
    run_id: str,
    model_fco: dict[str, Any],
    agent_fcos: list[dict[str, Any]],
    input_hashes: dict[str, str],
) -> dict[str, Any]:
    provisional = {
        "schema": "protein_hinge.fco.fanout_integration.v1",
        "fco_type": "fanout_integration",
        "run_id": run_id,
        "inputs": input_hashes,
        "model_object": model_fco["fco_id"],
        "agent_objects": sorted(fco["fco_id"] for fco in agent_fcos),
        "integration": {
            "dashboard_tabs": ["ELVIS", "AGENTS", "FIGURE", "VERIFY", "PROVE"],
            "database_projection": "db/build_db.py adds fco_object and fco_edge tables",
            "claim_ceiling": "REPURPOSING_HYPOTHESIS",
            "secret_policy": "OpenAI key used from local .env; key and key hash are not committed.",
        },
        "custody": {
            "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "calculation_version": "scripts/run_openai_fanout.py:v2",
        },
    }
    fco_hash = sha256_bytes(canonical(provisional))
    return {**provisional, "fco_id": fco_hash, "content_digest": fco_hash}


def build_merkle_root(fco_ids: list[str]) -> str:
    leaves = [bytes.fromhex(x.replace("sha256:", "")) for x in sorted(fco_ids)]
    if not leaves:
        return sha256_bytes(b"")
    while len(leaves) > 1:
        nxt = []
        for i in range(0, len(leaves), 2):
            left = leaves[i]
            right = leaves[i + 1] if i + 1 < len(leaves) else leaves[i]
            nxt.append(hashlib.sha256(b"\x01" + left + right).digest())
        leaves = nxt
    return "sha256:" + leaves[0].hex()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--env-file", help="Path to .env containing OPENAI_API_KEY")
    ap.add_argument("--model", help="OpenAI model override")
    ap.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    ap.add_argument("--max-workers", type=int, default=4)
    args = ap.parse_args()

    env, env_source = resolve_env(args.env_file)
    api_key = env.get("OPENAI_API_KEY") or env.get("OPENAPI_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY not found in .env or process environment")
    model = args.model or env.get("OPENAI_MODEL") or "gpt-4.1-nano"

    input_paths = {
        "cell_perturbation_figure": ROOT / "figures" / "cell_perturbation_restoration.png",
        "candidate_ranking": ROOT / "data" / "partner" / "candidate_ranking.csv",
        "mvp_status": ROOT / "docs" / "MVP_STATUS.md",
        "elvis_component_doc": ROOT / "docs" / "ELVIS_COMPONENT.md",
        "elvis_prescripted_demo": ROOT / "gap" / "elvis_prescripted_demo.json",
        "package_metadata": ROOT / "package.json",
        "plain_language_brief": ROOT / "docs" / "PLAIN_LANGUAGE_BRIEF.md",
        "ai_brief": ROOT / "docs" / "AI_PRESENTATION_BRIEF.json",
        "design_citations": ROOT / "docs" / "FCO_FCG_DESIGN_CITATIONS.md",
        "gap_lane_spec": ROOT / "docs" / "GAP_LANE_SPEC.md",
        "gap_lane_receipt": ROOT / "gap" / "runs" / "2026-08-13" / "receipt.json",
        "dashboard": ROOT / "site" / "index.html",
    }
    input_hashes = {
        key: sha256_file(path)
        for key, path in input_paths.items()
        if path.exists()
    }

    out_dir = OUT_ROOT / args.run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    fcos: list[dict[str, Any]] = []
    errors: list[str] = []
    started = time.time()
    with cf.ThreadPoolExecutor(max_workers=args.max_workers) as ex:
        future_map = {
            ex.submit(call_openai, api_key, model, agent, args.run_id): agent
            for agent in AGENTS
        }
        for fut in cf.as_completed(future_map):
            agent = future_map[fut]
            try:
                response = fut.result()
                fco = build_fco(
                    run_id=args.run_id,
                    agent=agent,
                    model=model,
                    env_source=env_source,
                    response=response,
                    input_hashes=input_hashes,
                )
                write_fco(out_dir / f"{agent['agent_id']}.fco.json", fco)
                fcos.append(fco)
                print(f"wrote FCO {agent['agent_id']} {fco['fco_id']}")
            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", errors="replace")[:500]
                errors.append(f"{agent['agent_id']}: HTTP {e.code}: {detail}")
            except Exception as e:
                errors.append(f"{agent['agent_id']}: {type(e).__name__}: {e}")

    model_fco = build_model_fco(
        run_id=args.run_id,
        model=model,
        env_source=env_source,
        response_models=[f.get("api", {}).get("model_returned") for f in fcos],
        input_hashes=input_hashes,
    )
    write_fco(out_dir / "model.openai.fco.json", model_fco)
    integration_fco = build_integration_fco(
        run_id=args.run_id,
        model_fco=model_fco,
        agent_fcos=fcos,
        input_hashes=input_hashes,
    )
    write_fco(out_dir / "integration.fco.json", integration_fco)

    object_ids = sorted([f["fco_id"] for f in fcos] + [model_fco["fco_id"], integration_fco["fco_id"]])
    manifest = {
        "schema": "protein_hinge.fco.agent_fanout_manifest.v1",
        "run_id": args.run_id,
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "duration_seconds": round(time.time() - started, 3),
        "model": model,
        "env_source": env_source,
        "api_key_committed": False,
        "input_hashes": input_hashes,
        "agent_fco_count": len(fcos),
        "object_count": len(object_ids),
        "model_fco_id": model_fco["fco_id"],
        "integration_fco_id": integration_fco["fco_id"],
        "agent_fco_ids": sorted(f["fco_id"] for f in fcos),
        "fco_ids": sorted(f["fco_id"] for f in fcos),
        "object_ids": object_ids,
        "merkle_root": build_merkle_root(object_ids),
        "errors": errors,
    }
    write_fco(out_dir / "manifest.fco.json", manifest)
    latest = OUT_ROOT / "latest.json"
    latest.write_text(json.dumps({"run_id": args.run_id, "path": str(out_dir.relative_to(ROOT))}, indent=2) + "\n")
    SITE_ASSETS.mkdir(parents=True, exist_ok=True)
    (SITE_ASSETS / "agent_fanout_latest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"wrote manifest {out_dir.relative_to(ROOT) / 'manifest.fco.json'}")
    if errors:
        print("errors:")
        for err in errors:
            print("  " + err)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
