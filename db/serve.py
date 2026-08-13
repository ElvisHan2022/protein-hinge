#!/usr/bin/env python3
"""
Serve the static query site locally.

Only reason this exists: a browser opening index.html from disk will not
fetch biocustody.db next to it, so the page falls back to asking you to pick
the file by hand. Serving the folder over HTTP removes that step. There is no
application here — the same files uploaded to any static host behave
identically, because all the work happens in the browser.

Run:  python3 db/serve.py     then open http://localhost:8000
"""
import http.server
import json
import os
import socketserver
import sys
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(os.path.dirname(HERE), "site")
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=SITE, **kw)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/elvis":
            self.serve_elvis_api(parsed.query)
            return
        super().do_GET()

    def send_json(self, payload, status=200):
        body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def serve_elvis_api(self, query):
        params = urllib.parse.parse_qs(query)
        disease = (params.get("q", ["Barth syndrome"])[0] or "Barth syndrome").strip()
        endpoint = "https://clinicaltrials.gov/api/v2/studies?" + urllib.parse.urlencode({
            "format": "json",
            "pageSize": "10",
            "query.cond": disease,
        })
        payload = {
            "schema": "protein_hinge.elvis.live_probe.v1",
            "mode": "live_clinicaltrials_probe",
            "query": disease,
            "claim_ceiling": "REPURPOSING_HYPOTHESIS",
            "source": endpoint,
            "rows": [],
            "abstentions": [],
            "note": (
                "Live mode currently probes ClinicalTrials.gov only. It does not "
                "claim the full Open Targets -> Convoke -> ClinicalTrials -> openFDA "
                "gap lane is wired."
            ),
        }
        try:
            req = urllib.request.Request(endpoint, headers={"User-Agent": "protein-hinge-demo/0.1"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            payload["abstentions"].append({
                "stage": "clinicaltrials_probe",
                "reason": f"{type(exc).__name__}: {exc}",
            })
            self.send_json(payload, status=502)
            return

        for study in data.get("studies", []):
            proto = study.get("protocolSection", {})
            ident = proto.get("identificationModule", {})
            status = proto.get("statusModule", {})
            design = proto.get("designModule", {})
            arms = proto.get("armsInterventionsModule", {})
            interventions = arms.get("interventions", []) or []
            names = [x.get("name") for x in interventions if x.get("name")]
            payload["rows"].append({
                "disease": disease,
                "nct_id": ident.get("nctId", ""),
                "title": ident.get("briefTitle", ""),
                "status": status.get("overallStatus", ""),
                "phase": ", ".join(design.get("phases", []) or []),
                "interventions": "; ".join(names[:5]),
                "grade": "ABSTAIN_LIVE_TARGET_PROGRAM_JOIN_NOT_WIRED",
                "custody": "live ClinicalTrials.gov response; not stored in FCG until captured",
            })
        if not payload["rows"]:
            payload["abstentions"].append({
                "stage": "clinicaltrials_probe",
                "reason": "No studies returned for condition query.",
            })
        self.send_json(payload)

    def end_headers(self):
        # Read-only, no caching. If you rebuild the database mid-demo, a
        # refresh must show the new one rather than a stale copy that quietly
        # disagrees with the store.
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):
        sys.stderr.write("  %s\n" % (fmt % args))


if not os.path.exists(os.path.join(SITE, "biocustody.db")):
    sys.exit("site/biocustody.db is missing. Run: python3 db/build_db.py")

socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"serving {SITE}")
    print("project Protein Hinge")
    print(f"open    http://localhost:{PORT}")
    print("        ctrl-c to stop")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print()
