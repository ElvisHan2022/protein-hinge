#!/usr/bin/env python3
"""AWS HealthOmics preflight with redacted output.

Extends scripts/aws_preflight.py for the HealthOmics lane. Checks, in order:

  1. boto3 importable
  2. a resolvable AWS credential (env vars or ~/.aws, either is fine)
  3. STS identity — masked to account last-4 and an ARN suffix
  4. HealthOmics reachable in the region; stores, workflows and runs listed
  5. whether the annotation-store API is permitted (it is SCP-denied in the
     event account, and that denial is recorded as an abstention, not hidden)

Writes model_trace/healthomics_status.json and site/assets/healthomics_status.json.
No secret ever appears in either file. Every failure is a named abstention,
not a crash — the dashboard renders whatever state this reports.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "model_trace" / "healthomics_status.json"
SITE_ASSETS = ROOT / "site" / "assets"

DEFAULT_REGION = "us-east-1"


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
    load_dotenv(ROOT / ".env")
    region = os.environ.get("AWS_DEFAULT_REGION") or os.environ.get("AWS_REGION") or DEFAULT_REGION
    payload = {
        "schema": "protein_hinge.healthomics_preflight.v1",
        "checked_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "credentials_committed": False,
        "region": region,
        "status": "unknown",
        "identity": None,
        "abstentions": [],
    }

    def finish(status: str) -> int:
        payload["status"] = status
        OUT.parent.mkdir(exist_ok=True)
        SITE_ASSETS.mkdir(parents=True, exist_ok=True)
        text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        OUT.write_text(text)
        (SITE_ASSETS / "healthomics_status.json").write_text(text)
        print(f"status {status}")
        print(f"wrote {OUT.relative_to(ROOT)}")
        return 0

    try:
        import boto3
        import botocore.exceptions
    except ImportError:
        payload["abstentions"].append({"stage": "boto3", "reason": "boto3 not installed"})
        return finish("boto3_missing")

    session = boto3.session.Session(region_name=region)
    if session.get_credentials() is None:
        payload["abstentions"].append({
            "stage": "credentials",
            "reason": ("No AWS credentials found in the environment or ~/.aws. "
                       "Put event credentials in .env and re-run this script."),
        })
        return finish("missing_credentials")

    try:
        ident = session.client("sts").get_caller_identity()
        arn = str(ident.get("Arn", ""))
        payload["identity"] = {
            "account_last4": str(ident.get("Account", ""))[-4:],
            "arn_suffix": arn[-32:],
        }
    except botocore.exceptions.BotoCoreError as exc:
        payload["abstentions"].append({"stage": "sts", "reason": f"{type(exc).__name__}: {exc}"})
        return finish("identity_check_failed")
    except botocore.exceptions.ClientError as exc:
        payload["abstentions"].append({"stage": "sts", "reason": f"{type(exc).__name__}: {exc}"})
        return finish("identity_check_failed")

    try:
        omics = session.client("omics")
        payload["stores"] = []
        payload["workflows"] = []
        payload["runs"] = []
        for s in omics.list_reference_stores(maxResults=10).get("referenceStores", []):
            payload["stores"].append({"kind": "reference", "name": s.get("name")})
        for s in omics.list_sequence_stores(maxResults=10).get("sequenceStores", []):
            payload["stores"].append({"kind": "sequence", "name": s.get("name")})
        for w in omics.list_workflows(type="PRIVATE", maxResults=10).get("items", []):
            payload["workflows"].append(w.get("name"))
        for r in omics.list_runs(maxResults=20).get("items", []):
            name = r.get("name") or ""
            payload["runs"].append({
                "name": name, "status": r.get("status"),
                "ours": name.startswith("protein-hinge-"),
            })
        try:
            omics.list_annotation_stores(maxResults=1)
        except Exception as exc:
            payload["abstentions"].append({
                "stage": "annotation_stores",
                "reason": ("Denied by the event's service control policy "
                           "(deprecated API surface); the workflow lane is the "
                           f"sanctioned path. Receipt: {str(exc)[:150]}"),
            })
        return finish("ok" if payload["workflows"] else "workflow_surface_empty")
    except Exception as exc:
        payload["abstentions"].append({"stage": "omics", "reason": f"{type(exc).__name__}: {exc}"})
        return finish("omics_unreachable")


if __name__ == "__main__":
    raise SystemExit(main())
