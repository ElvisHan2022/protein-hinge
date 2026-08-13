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
import os
import socketserver
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(os.path.dirname(HERE), "site")
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=SITE, **kw)

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
