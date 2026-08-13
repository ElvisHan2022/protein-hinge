#!/usr/bin/env python3
"""Local AWS credential preflight with redacted output."""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "model_trace" / "aws_preflight.json"
SITE_ASSETS = ROOT / "site" / "assets"


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def masked(value: str | None) -> str:
    if not value:
        return "missing"
    if len(value) <= 8:
        return "present"
    return value[:4] + "..." + value[-4:]


def main() -> int:
    load_dotenv(ROOT / ".env")
    required = ["AWS_DEFAULT_REGION", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"]
    env_status = {k: masked(os.environ.get(k)) for k in required}
    missing = [k for k in required if not os.environ.get(k)]
    payload = {
        "schema": "protein_hinge.aws_preflight.v1",
        "checked_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "credentials_committed": False,
        "env_status": env_status,
        "aws_cli": "not_checked",
        "identity": None,
        "status": "missing_credentials" if missing else "credentials_present",
        "missing": missing,
    }
    if not missing:
        try:
            proc = subprocess.run(
                ["aws", "sts", "get-caller-identity", "--output", "json"],
                text=True,
                capture_output=True,
                timeout=12,
                check=True,
                env=os.environ.copy(),
            )
            ident = json.loads(proc.stdout)
            payload["aws_cli"] = "ok"
            payload["identity"] = {
                "account": ident.get("Account"),
                "arn_suffix": str(ident.get("Arn", ""))[-24:],
                "user_id_suffix": str(ident.get("UserId", ""))[-12:],
            }
            payload["status"] = "ok"
        except FileNotFoundError:
            payload["aws_cli"] = "missing"
            payload["status"] = "aws_cli_missing"
        except Exception as exc:
            payload["aws_cli"] = "error"
            payload["status"] = "aws_check_failed"
            payload["error"] = f"{type(exc).__name__}: {exc}"

    OUT.parent.mkdir(exist_ok=True)
    SITE_ASSETS.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    OUT.write_text(text)
    (SITE_ASSETS / "aws_preflight.json").write_text(text)
    print(f"status {payload['status']}")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0 if payload["status"] in {"ok", "credentials_present", "missing_credentials", "aws_cli_missing"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
