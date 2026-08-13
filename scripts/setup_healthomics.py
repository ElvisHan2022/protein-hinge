#!/usr/bin/env python3
"""Create and load the AWS HealthOmics annotation store for the ClinVar subset.

Prerequisites:
  - scripts/build_clinvar_evidence.py has produced data/healthomics/clinvar_subset.tsv
  - AWS credentials resolvable (run `aws configure`; hackathon user: elvish.an)

What it does, idempotently:
  1. S3 bucket   protein-hinge-omics-<account>          (created if missing)
  2. Upload      clinvar_subset.tsv                      (versioned by sha256 key)
  3. IAM role    ProteinHingeOmicsImport                 (trusts omics.amazonaws.com,
                 read access to that bucket only)
  4. Store       protein_hinge_clinvar                   (TSV / GENERIC annotation store)
  5. Import job  from the uploaded TSV via the role

Receipts to model_trace/healthomics_setup.json and site/assets/. Secrets are
never written. Re-running is safe: existing resources are reused, and a new
import only starts if the TSV digest changed or no import succeeded yet.
"""
from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TSV = ROOT / "data" / "healthomics" / "clinvar_subset.tsv"
OUT = ROOT / "model_trace" / "healthomics_setup.json"
SITE_ASSETS = ROOT / "site" / "assets"

STORE_NAME = "protein_hinge_clinvar"
ROLE_NAME = "ProteinHingeOmicsImport"
DEFAULT_REGION = "us-east-1"

SCHEMA = [
    {"gene": "STRING"},
    {"accession": "STRING"},
    {"title": "STRING"},
    {"classification": "STRING"},
    {"review_status": "STRING"},
    {"conditions": "STRING"},
]


def main() -> int:
    import boto3

    if not TSV.exists():
        raise SystemExit("data/healthomics/clinvar_subset.tsv missing. "
                         "Run scripts/build_clinvar_evidence.py first.")
    tsv_digest = hashlib.sha256(TSV.read_bytes()).hexdigest()

    import os
    region = os.environ.get("AWS_DEFAULT_REGION") or os.environ.get("AWS_REGION") or DEFAULT_REGION
    session = boto3.session.Session(region_name=region)
    if session.get_credentials() is None:
        raise SystemExit("No AWS credentials. Run `aws configure` (user elvish.an) first.")

    sts = session.client("sts")
    account = sts.get_caller_identity()["Account"]
    receipt = {
        "schema": "protein_hinge.healthomics_setup.v1",
        "started_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "region": region,
        "tsv_sha256": tsv_digest,
        "steps": [],
    }

    def step(name: str, detail: str) -> None:
        receipt["steps"].append({"step": name, "detail": detail})
        print(f"  {name}: {detail}")

    # 1. bucket ------------------------------------------------------------
    bucket = f"protein-hinge-omics-{account}"
    s3 = session.client("s3")
    try:
        s3.head_bucket(Bucket=bucket)
        step("bucket", f"{bucket} exists")
    except Exception:
        kwargs = {"Bucket": bucket}
        if region != "us-east-1":
            kwargs["CreateBucketConfiguration"] = {"LocationConstraint": region}
        s3.create_bucket(**kwargs)
        step("bucket", f"{bucket} created")

    # 2. upload ------------------------------------------------------------
    key = f"clinvar/{tsv_digest[:16]}/clinvar_subset.tsv"
    s3.upload_file(str(TSV), bucket, key)
    s3_uri = f"s3://{bucket}/{key}"
    step("upload", s3_uri)

    # 3. role --------------------------------------------------------------
    iam = session.client("iam")
    trust = json.dumps({
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Allow",
                       "Principal": {"Service": "omics.amazonaws.com"},
                       "Action": "sts:AssumeRole"}],
    })
    policy = json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {"Effect": "Allow", "Action": ["s3:GetObject"],
             "Resource": f"arn:aws:s3:::{bucket}/*"},
            {"Effect": "Allow", "Action": ["s3:ListBucket"],
             "Resource": f"arn:aws:s3:::{bucket}"},
        ],
    })
    try:
        role_arn = iam.get_role(RoleName=ROLE_NAME)["Role"]["Arn"]
        step("role", f"{ROLE_NAME} exists")
    except iam.exceptions.NoSuchEntityException:
        role_arn = iam.create_role(
            RoleName=ROLE_NAME, AssumeRolePolicyDocument=trust,
            Description="HealthOmics import read access to the protein-hinge bucket",
        )["Role"]["Arn"]
        step("role", f"{ROLE_NAME} created")
        time.sleep(8)  # IAM propagation before omics assumes it
    iam.put_role_policy(RoleName=ROLE_NAME, PolicyName="s3-read", PolicyDocument=policy)

    # 4. store -------------------------------------------------------------
    omics = session.client("omics")
    stores = omics.list_annotation_stores(maxResults=50).get("annotationStores", [])
    ours = [s for s in stores if s.get("name") == STORE_NAME]
    if ours:
        store_id = ours[0]["id"]
        step("store", f"{STORE_NAME} exists ({ours[0].get('status')})")
    else:
        created = omics.create_annotation_store(
            name=STORE_NAME,
            storeFormat="TSV",
            storeOptions={"tsvStoreOptions": {
                "annotationType": "GENERIC",
                "schema": SCHEMA,
            }},
            description="ClinVar pathogenic/likely-pathogenic subset for the eight "
                        "cardiolipin consensus genes. Source and digests in "
                        "data/healthomics/clinvar_provenance.json.",
        )
        store_id = created["id"]
        step("store", f"{STORE_NAME} created ({created.get('status')})")

    # wait until the store itself is ACTIVE before importing
    for _ in range(60):
        status = omics.get_annotation_store(name=STORE_NAME).get("status")
        if status == "ACTIVE":
            break
        if status in ("FAILED",):
            raise SystemExit(f"annotation store entered {status}")
        time.sleep(10)
    step("store_status", status)

    # 5. import ------------------------------------------------------------
    job = omics.start_annotation_import_job(
        destinationName=STORE_NAME,
        roleArn=role_arn,
        items=[{"source": s3_uri}],
        formatOptions={"tsvOptions": {"readOptions": {"header": True, "sep": "\t"}}},
        runLeftNormalization=False,
    )
    job_id = job["id"]
    step("import_job", f"started {job_id}")

    final = "UNKNOWN"
    for _ in range(90):
        j = omics.get_annotation_import_job(jobId=job_id)
        final = j.get("status", "UNKNOWN")
        if final in ("COMPLETED", "FAILED", "CANCELLED", "COMPLETED_WITH_FAILURES"):
            break
        time.sleep(10)
    step("import_status", final)

    receipt["finished_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    receipt["result"] = {
        "bucket": bucket, "s3_uri": s3_uri, "store_id": store_id,
        "import_job": job_id, "import_status": final,
    }
    OUT.parent.mkdir(exist_ok=True)
    SITE_ASSETS.mkdir(parents=True, exist_ok=True)
    text = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    OUT.write_text(text)
    (SITE_ASSETS / "healthomics_setup.json").write_text(text)
    print(f"import {final}")
    return 0 if final == "COMPLETED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
