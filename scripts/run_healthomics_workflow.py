#!/usr/bin/env python3
"""Protein Hinge x AWS HealthOmics, event-account edition.

The hackathon account denies the (deprecated) annotation-store APIs by
service control policy — that denial is recorded as a receipt, not hidden.
The sanctioned HealthOmics surface is workflows + S3 + Athena, so this script:

  1. uploads our ClinVar evidence (TSV + provenance digests) to the event's
     omics output bucket under protein-hinge/
  2. starts a VEP annotation run on the event's vep-annotation-workflow,
     cloned from the account's own completed reference run
  3. writes a receipt to model_trace/ and site/assets/

Idempotent-ish: re-running uploads the same digested objects and starts a new
run (runs are timestamped by name).
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "model_trace" / "healthomics_workflow.json"
SITE_ASSETS = ROOT / "site" / "assets"

REGION = "us-east-1"
BUCKET = None  # resolved: omics-output-us-east-1-<account>
WORKFLOW_NAME = "vep-annotation-workflow"


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def main() -> int:
    import boto3

    load_dotenv(ROOT / ".env")
    session = boto3.session.Session(region_name=REGION)
    sts = session.client("sts")
    account = sts.get_caller_identity()["Account"]
    bucket = f"omics-output-{REGION}-{account}"
    s3 = session.client("s3")
    omics = session.client("omics")
    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y%m%d-%H%M%S")

    receipt = {
        "schema": "protein_hinge.healthomics_workflow.v1",
        "started_at": now.replace(microsecond=0).isoformat(),
        "account": account,
        "region": REGION,
        "steps": [],
    }

    def step(name: str, detail) -> None:
        receipt["steps"].append({"step": name, "detail": detail})
        print(f"  {name}: {detail}")

    # 1. upload evidence ---------------------------------------------------
    uploads = {}
    for local in ("data/healthomics/clinvar_subset.tsv",
                  "data/healthomics/clinvar_provenance.json"):
        p = ROOT / local
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        key = f"protein-hinge/clinvar/{digest[:16]}/{p.name}"
        s3.upload_file(str(p), bucket, key)
        uploads[p.name] = {"s3_uri": f"s3://{bucket}/{key}", "sha256": digest}
        step("upload", uploads[p.name]["s3_uri"])
    receipt["evidence_uploads"] = uploads

    # 2. start a VEP run cloned from the account's reference run -----------
    wfs = omics.list_workflows(type="PRIVATE", maxResults=10).get("items", [])
    wf = next((w for w in wfs if w.get("name") == WORKFLOW_NAME), None)
    if wf is None:
        step("workflow", f"{WORKFLOW_NAME} not found; skipping run")
        receipt["run"] = None
    else:
        ref_runs = [r for r in omics.list_runs(maxResults=20).get("items", [])
                    if "vep" in (r.get("name") or "").lower()]
        ref = omics.get_run(id=ref_runs[0]["id"]) if ref_runs else {}
        params = ref.get("parameters") or {}
        try:
            run = omics.start_run(
                workflowId=wf["id"],
                workflowType="PRIVATE",
                name=f"protein-hinge-vep-{stamp}",
                roleArn=ref.get("roleArn"),
                outputUri=f"s3://{bucket}/vep-annotation/runs/",
                parameters=params,
                storageType="DYNAMIC",
            )
            receipt["run"] = {
                "id": run.get("id"), "name": f"protein-hinge-vep-{stamp}",
                "workflow": WORKFLOW_NAME, "status": run.get("status"),
                "parameters_cloned_from": ref_runs[0].get("name"),
            }
            step("start_run", f"{run.get('id')} ({run.get('status')})")
        except Exception as exc:
            receipt["run"] = None
            receipt["run_error"] = f"{type(exc).__name__}: {exc}"
            step("start_run", f"denied/failed: {type(exc).__name__}")

    OUT.parent.mkdir(exist_ok=True)
    SITE_ASSETS.mkdir(parents=True, exist_ok=True)
    text = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    OUT.write_text(text)
    (SITE_ASSETS / "healthomics_workflow.json").write_text(text)
    print("wrote model_trace/healthomics_workflow.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
