#!/usr/bin/env python3
"""Capture small official regulatory source surfaces for the demo."""

import hashlib
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import urllib.request
import zipfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "regulatory"
OUT = ROOT / "model_trace" / "regulatory_source_surfaces.json"
SITE_OUT = ROOT / "site" / "assets" / "regulatory_source_surfaces.json"
USER_AGENT = "protein-hinge-demo/0.1"
CAPTURED_ON = "2026-08-13"


SOURCES = [
    {
        "key": "ema_medicines_report",
        "region_or_scope": "Europe",
        "source_type": "xlsx",
        "url": "https://www.ema.europa.eu/en/documents/report/medicines-output-medicines-report_en.xlsx",
        "local_name": "ema_medicines_report.xlsx",
        "claim": "Small official EMA medicines workbook captured and hashed; not normalized into a full global approval database.",
    },
    {
        "key": "ema_orphan_designations_report",
        "region_or_scope": "Europe",
        "source_type": "xlsx",
        "url": "https://www.ema.europa.eu/en/documents/report/medicines-output-orphan_designations-report_en.xlsx",
        "local_name": "ema_orphan_designations_report.xlsx",
        "claim": "Small official EMA orphan-designations workbook captured and hashed; used as source-surface evidence only.",
    },
    {
        "key": "pmda_approved_products_page",
        "region_or_scope": "Japan",
        "source_type": "html",
        "url": "https://www.pmda.go.jp/english/review-services/reviews/approved-information/drugs/0002.html",
        "local_name": "pmda_approved_products_page.html",
        "claim": "Official PMDA approved-products page captured and hashed; page points to a larger PDF list that is not vendored.",
    },
    {
        "key": "fda_orphan_search_page",
        "region_or_scope": "United States",
        "source_type": "html",
        "url": "https://www.accessdata.fda.gov/scripts/opdlisting/oopd/",
        "local_name": "fda_orphan_search_page.html",
        "claim": "Official FDA orphan-designation search surface captured and hashed; web-form query results are not normalized here.",
    },
]


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links = []
        self._href = None
        self._text = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._text = []

    def handle_data(self, data):
        if self._href is not None:
            text = data.strip()
            if text:
                self._text.append(text)

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            self.links.append({"href": self._href, "text": " ".join(self._text)})
            self._href = None
            self._text = []


def fetch(url: str) -> tuple[bytes, dict]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=45) as resp:
        body = resp.read()
        meta = {
            "http_status": resp.status,
            "content_type": resp.headers.get("content-type"),
            "final_url": resp.url,
        }
    return body, meta


def sha256_bytes(body: bytes) -> str:
    return "sha256:" + hashlib.sha256(body).hexdigest()


def xlsx_preview(path: Path) -> dict:
    ns = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(path) as zf:
        shared = []
        if "xl/sharedStrings.xml" in zf.namelist():
            root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for si in root.findall("a:si", ns):
                shared.append("".join(t.text or "" for t in si.findall(".//a:t", ns)))
        sheet_name = "xl/worksheets/sheet1.xml"
        root = ET.fromstring(zf.read(sheet_name))
        rows = []
        row_count = 0
        for row in root.findall("a:sheetData/a:row", ns):
            row_count += 1
            if len(rows) >= 4:
                continue
            vals = []
            for cell in row.findall("a:c", ns):
                v = cell.find("a:v", ns)
                if v is None:
                    vals.append("")
                elif cell.get("t") == "s":
                    vals.append(shared[int(v.text)])
                else:
                    vals.append(v.text or "")
            rows.append(vals)
        return {
            "sheet": sheet_name,
            "row_count_in_first_sheet": row_count,
            "preview_rows": rows,
        }


def html_preview(path: Path, key: str) -> dict:
    text = path.read_text(errors="replace")
    title_match = re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S)
    title = html.unescape(re.sub(r"\s+", " ", title_match.group(1)).strip()) if title_match else ""
    parser = LinkParser()
    parser.feed(text)
    links = []
    for link in parser.links:
        label = link["text"]
        href = link["href"]
        if key.startswith("pmda") and ("Approved" in label or "/files/" in href):
            links.append(link)
        elif key.startswith("fda") and ("Excel" in label or "instructions" in label.lower()):
            links.append(link)
    return {
        "title": title,
        "selected_links": links[:8],
        "mentions": {
            "excel": "Excel" in text or "excel" in text,
            "approved": "Approved" in text or "approved" in text,
            "orphan": "Orphan" in text or "orphan" in text,
        },
    }


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    records = []
    for source in SOURCES:
        body, meta = fetch(source["url"])
        local_path = DATA / source["local_name"]
        local_path.write_bytes(body)
        record = {
            "schema": "protein_hinge.regulatory_source_surface.v1",
            "key": source["key"],
            "region_or_scope": source["region_or_scope"],
            "source_type": source["source_type"],
            "url": source["url"],
            "final_url": meta["final_url"],
            "http_status": meta["http_status"],
            "content_type": meta["content_type"],
            "captured_on": CAPTURED_ON,
            "not_date_pinned": True,
            "local_path": str(local_path.relative_to(ROOT)),
            "bytes": len(body),
            "sha256": sha256_bytes(body),
            "claim": source["claim"],
        }
        if source["source_type"] == "xlsx":
            record["preview"] = xlsx_preview(local_path)
        else:
            record["preview"] = html_preview(local_path, source["key"])
        records.append(record)

    payload = {
        "schema": "protein_hinge.regulatory_source_surfaces.v1",
        "status": "source_surfaces_captured_not_full_ingestion",
        "captured_on": CAPTURED_ON,
        "claim_boundary": (
            "Official source surfaces and small workbooks are captured for "
            "traceability. This is not a full FDA/EMA/PMDA approved-drug database."
        ),
        "reverify_caveat": (
            "These official sources are live web resources. Re-fetching later may "
            "produce different bytes; that is a source-corpus change rather than "
            "a silent mutation of this committed capture."
        ),
        "sources": records,
    }
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    OUT.write_text(text)
    SITE_OUT.write_text(text)
    for rec in records:
        print(f"{rec['key']}: {rec['bytes']} bytes {rec['sha256']}")
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"wrote {SITE_OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
