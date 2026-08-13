#!/usr/bin/env python3
"""AWS HealthOmics preflight with redacted output.

Extends scripts/aws_preflight.py for the HealthOmics lane. Checks, in order:

  1. boto3 importable
  2. a resolvable AWS credential (env vars or ~/.aws, either is fine)
  3. STS identity — masked; compared against the expected hackathon user
  4. HealthOmics reachable in the region; annotation stores listed
  5. whether the protein_hinge_clinvar store exists and its status

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

EXPECTED_USERNAME = "elvish.an"
STORE_NAME = "protein_hinge_clinvar"
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
        "expected_username": EXPECTED_USERNAME,
        "store_name": STORE_NAME,
        "status": "unknown",
        "identity": None,
        "identity_matches_expected": None,
        "annotation_stores": [],
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
                       f"Run `aws configure` as {EXPECTED_USERNAME} and re-run this script."),
        })
        return finish("missing_credentials")

    try:
        ident = session.client("sts").get_caller_identity()
        arn = str(ident.get("Arn", ""))
        payload["identity"] = {
            "account": ident.get("Account"),
            "arn_suffix": arn[-32:],
        }
        payload["identity_matches_expected"] = EXPECTED_USERNAME in arn
    except botocore.exceptions.BotoCoreError as exc:
        payload["abstentions"].append({"stage": "sts", "reason": f"{type(exc).__name__}: {exc}"})
        return finish("identity_check_failed")
    except botocore.exceptions.ClientError as exc:
        payload["abstentions"].append({"stage": "sts", "reason": f"{type(exc).__name__}: {exc}"})
        return finish("identity_check_failed")

    try:
        omics = session.client("omics")
        stores = omics.list_annotation_stores(maxResults=50).get("annotationStores", [])
        for s in stores:
            payload["annotation_stores"].append({
                "name": s.get("name"),
                "status": s.get("status"),
                "format": s.get("storeFormat"),
                "size_bytes": s.get("storeSizeBytes"),
            })
        ours = [s for s in stores if s.get("name") == STORE_NAME]
        if not ours:
            payload["abstentions"].append({
                "stage": "annotation_store",
                "reason": (f"Store {STORE_NAME} not found. "
                           "Run scripts/setup_healthomics.py to create and load it."),
            })
            return finish("store_missing")
        return finish("ok" if ours[0].get("status") == "ACTIVE" else "store_not_active")
    except Exception as exc:
        payload["abstentions"].append({"stage": "omics", "reason": f"{type(exc).__name__}: {exc}"})
        return finish("omics_unreachable")


if __name__ == "__main__":
    raise SystemExit(main())
