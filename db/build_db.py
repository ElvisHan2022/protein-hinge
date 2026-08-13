#!/usr/bin/env python3
"""
Materialize the custody graph into a single queryable SQLite database.

WHY THIS EXISTS
---------------
`fcg/store/` is already a database: content-addressed, append-only, keyed by
hash. What it cannot do is answer a question. "Which sources are attested but
not held?" requires opening 62 files and writing a loop. This file turns the
store into something you can ask.

WHAT IT IS NOT
--------------
It is not the ledger. The ledger is the store. This is a *projection* of the
store, and it is regenerated from the store, never edited. If the two ever
disagree, the store is right and this file is stale.

DIRECTION OF DEPENDENCE
-----------------------
The database is downstream of the Merkle root and must never be upstream of it.
Hashing the .db into the graph would be circular: the digest would change the
graph, which would change the .db, which would change the digest. So the root
goes *into* the database, and the database's own digest is published beside it
in publish_manifest.json. Downstream artifacts get manifests; inputs get nodes.

DETERMINISM
-----------
Built with a fixed page size, rows inserted in sorted order, no autoincrement,
no wall-clock values. Two builds of the same store produce byte-identical
files, which is what makes the .db digest in the manifest meaningful.

Run:  python3 db/build_db.py
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
STORE = os.path.join(REPO, "fcg", "store")
OUT = os.path.join(HERE, "biocustody.db")

sys.path.insert(0, os.path.join(REPO, "fcg"))
sys.path.insert(0, os.path.join(REPO, "fto"))

from fcg import canonical, merkle_root, _leaf_hash  # noqa: E402


def jload(*parts):
    with open(os.path.join(*parts)) as fh:
        return json.load(fh)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


SCHEMA = """
PRAGMA page_size = 4096;
PRAGMA journal_mode = DELETE;

-- ---------------------------------------------------------------- meta
CREATE TABLE meta (
  key    TEXT PRIMARY KEY,
  value  TEXT NOT NULL,
  note   TEXT
);

-- ---------------------------------------------------------------- nodes
-- One row per node. record_json is the full canonical record, so no query
-- here can lose information that the store holds; the columns are a
-- convenience, not a replacement.
CREATE TABLE node (
  node_id         TEXT PRIMARY KEY,
  label           TEXT NOT NULL,
  kind            TEXT NOT NULL,      -- SOURCE | DERIVATION | CLAIM
  layer           INTEGER NOT NULL,   -- 0 sources .. 3 claims
  content_digest  TEXT NOT NULL,
  bytes           INTEGER,
  bytes_held      INTEGER NOT NULL,   -- 1 => we hold them => RECOMPUTED
  evidence_level  TEXT NOT NULL,      -- RECOMPUTED | COMMITTED
  recompute_kind  TEXT,               -- bytes_identity | origin_attestation | function
  origin          TEXT,
  captured_at     TEXT,
  leaf_index      INTEGER NOT NULL,   -- position in the merkle tree
  leaf_hash       TEXT NOT NULL,
  record_json     TEXT NOT NULL
);
CREATE INDEX ix_node_kind  ON node(kind);
CREATE INDEX ix_node_layer ON node(layer);
CREATE INDEX ix_node_label ON node(label);

-- ---------------------------------------------------------------- edges
-- edge(node_id consumes input_id). Direction is "consumes", so a rejection
-- propagates along edges from input_id to node_id.
CREATE TABLE edge (
  node_id   TEXT NOT NULL REFERENCES node(node_id),
  input_id  TEXT NOT NULL REFERENCES node(node_id),
  position  INTEGER NOT NULL,
  PRIMARY KEY (node_id, position)
);
CREATE INDEX ix_edge_input ON edge(input_id);

-- ---------------------------------------------------------------- sources
CREATE TABLE source (
  node_id       TEXT PRIMARY KEY REFERENCES node(node_id),
  uri           TEXT,
  http_status   INTEGER,
  nbytes        INTEGER,
  dataset       TEXT,
  source_site   TEXT,
  plate         TEXT,
  plate_type    TEXT,
  batch         TEXT,
  registry      TEXT,
  registry_name TEXT,
  lane          TEXT,
  corpus_date   TEXT,
  capture_method TEXT,
  reverify_by   TEXT,
  recomputable_offline INTEGER,
  not_date_pinned INTEGER
);

-- ---------------------------------------------------------------- derivations
CREATE TABLE derivation (
  node_id      TEXT PRIMARY KEY REFERENCES node(node_id),
  fn           TEXT NOT NULL,
  params_json  TEXT,
  payload_json TEXT
);

-- ---------------------------------------------------------------- claims
CREATE TABLE claim (
  node_id       TEXT PRIMARY KEY REFERENCES node(node_id),
  statement     TEXT NOT NULL,
  level         TEXT NOT NULL,
  claim_ceiling TEXT NOT NULL,
  hedge         TEXT,
  lane          TEXT,
  fto_level     TEXT,
  evidence_json TEXT
);

-- ---------------------------------------------------------------- atoms
-- The held bytes. These are the difference between RECOMPUTED and COMMITTED:
-- without them a reader can only take the digests on trust.
CREATE TABLE atom (
  digest  TEXT PRIMARY KEY,
  nbytes  INTEGER NOT NULL,
  body    BLOB NOT NULL
);

-- ---------------------------------------------------------------- merkle
CREATE TABLE merkle_leaf (
  leaf_index INTEGER PRIMARY KEY,
  node_id    TEXT NOT NULL REFERENCES node(node_id),
  leaf_hash  TEXT NOT NULL
);

-- An inclusion proof is only a proof against ONE tree. The route written by
-- fcg/ingest.py proves membership in the 41-leaf science-only tree; the FTO
-- lane then extends the graph to 62 leaves and a different root. Both routes
-- are correct, and replaying the older one against the current root fails --
-- correctly. So every route carries the root it was computed against, and
-- is_current says whether that is still the root of record. Storing routes
-- without this column would reproduce, in the custody layer, exactly the
-- stale-search reuse that fto.py hashes corpus_date to prevent.
CREATE TABLE merkle_route (
  node_id     TEXT NOT NULL REFERENCES node(node_id),
  step        INTEGER NOT NULL,
  side        TEXT NOT NULL,     -- which side the SIBLING sits on
  sibling     TEXT NOT NULL,
  merkle_root TEXT NOT NULL,     -- the tree this proof is against
  leaf_index  INTEGER,
  is_current  INTEGER NOT NULL,  -- 0 => proof for a superseded tree
  PRIMARY KEY (node_id, step)
);

-- ---------------------------------------------------------------- science
CREATE TABLE consensus_gene (
  symbol    TEXT PRIMARY KEY,
  jcp_id    TEXT NOT NULL,
  entrez    INTEGER,
  well      TEXT NOT NULL,
  tier      INTEGER NOT NULL,
  rationale TEXT NOT NULL
);

-- ---------------------------------------------------------------- FTO
CREATE TABLE registry_query (
  registry     TEXT NOT NULL,
  label        TEXT NOT NULL,
  endpoint     TEXT,
  http_status  INTEGER,
  nbytes       INTEGER,
  sha256       TEXT NOT NULL,
  result_count INTEGER,
  corpus_date  TEXT NOT NULL,
  params_json  TEXT,
  gene         TEXT,
  ensembl      TEXT,
  sm_tractability_buckets INTEGER,
  drug_candidates         INTEGER,
  associated_diseases     INTEGER,
  PRIMARY KEY (registry, label)
);

CREATE TABLE registry_status (
  registry TEXT PRIMARY KEY,
  name     TEXT NOT NULL,
  lane     TEXT NOT NULL,
  wired    INTEGER NOT NULL,
  blocker  TEXT
);

-- ---------------------------------------------------------------- tamper
CREATE TABLE tamper_assertion (
  name    TEXT PRIMARY KEY,
  passed  INTEGER NOT NULL
);

-- ---------------------------------------------------------------- FCO
-- First-class projection of generated Fractal Custody Objects. The JSON files
-- remain the objects of record; this table makes them queryable in the demo DB.
CREATE TABLE fco_object (
  fco_id          TEXT PRIMARY KEY,
  run_id          TEXT NOT NULL,
  fco_type        TEXT NOT NULL,
  schema          TEXT NOT NULL,
  label           TEXT NOT NULL,
  role            TEXT,
  model           TEXT,
  content_digest  TEXT NOT NULL,
  object_sha256   TEXT NOT NULL,
  record_json     TEXT NOT NULL
);

CREATE TABLE fco_edge (
  source_id TEXT NOT NULL,
  target_id TEXT NOT NULL,
  relation  TEXT NOT NULL,
  PRIMARY KEY (source_id, target_id, relation)
);

-- ---------------------------------------------------------------- GAP
CREATE TABLE gap_candidate (
  disease           TEXT NOT NULL,
  target_symbol     TEXT NOT NULL,
  target_reconcile  TEXT NOT NULL,
  alias_used        TEXT,
  association_score REAL,
  drug_program      TEXT NOT NULL,
  company           TEXT,
  modality          TEXT,
  stage             TEXT,
  prior_trials      TEXT,
  n_trials          INTEGER NOT NULL,
  rule_fired        TEXT NOT NULL,
  grade             TEXT NOT NULL
);

CREATE TABLE gap_receipt (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

-- ---------------------------------------------------------------- trace/context
CREATE TABLE model_trace_record (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE model_trace_model (
  model      TEXT NOT NULL,
  family     TEXT,
  size       TEXT,
  status     TEXT,
  trace_role TEXT
);

CREATE TABLE hackathon_context (
  item               TEXT PRIMARY KEY,
  integration_status TEXT NOT NULL,
  demo_language      TEXT NOT NULL,
  why_it_matters     TEXT NOT NULL
);

-- ================================================================ views
-- The questions the file store could not answer.

-- What do we actually hold, versus what are we taking on trust?
CREATE VIEW v_evidence_posture AS
SELECT evidence_level,
       kind,
       COUNT(*)      AS nodes,
       SUM(bytes)    AS total_bytes
FROM node
GROUP BY evidence_level, kind
ORDER BY evidence_level, kind;

-- The honest list: asserted at origin, bytes not in our possession.
CREATE VIEW v_attested_not_held AS
SELECT n.label, s.uri, s.nbytes, s.http_status, s.reverify_by
FROM node n JOIN source s USING (node_id)
WHERE n.bytes_held = 0
ORDER BY n.label;

-- Every claim with its ceiling, so nobody has to trust a summary.
CREATE VIEW v_claims AS
SELECT n.label, c.lane, c.level, c.claim_ceiling, c.fto_level, c.statement
FROM node n JOIN claim c USING (node_id)
ORDER BY n.layer, n.label;

-- The finding that most affects the project, as a table rather than a sentence.
CREATE VIEW v_tractability AS
SELECT gene, ensembl,
       sm_tractability_buckets AS sm_buckets,
       drug_candidates,
       associated_diseases,
       CASE WHEN sm_tractability_buckets = 0 THEN 'undrugged' ELSE 'has chemistry' END AS verdict
FROM registry_query
WHERE registry = 'open_targets' AND gene IS NOT NULL
ORDER BY sm_tractability_buckets DESC, gene;

-- Full ancestry of any node, walking edges upward to the sources it rests on.
-- MIN(depth) collapses diamonds: a node reachable by two paths of different
-- length is one ancestor, not two, and counting it twice would inflate every
-- footprint below.
CREATE VIEW v_custody_chain AS
WITH RECURSIVE up(root_id, node_id, depth) AS (
  SELECT node_id, node_id, 0 FROM node
  UNION
  SELECT up.root_id, e.input_id, up.depth + 1
  FROM up JOIN edge e ON e.node_id = up.node_id
)
SELECT up.root_id,
       r.label     AS root_label,
       MIN(up.depth) AS depth,
       up.node_id  AS ancestor_id,
       n.label     AS ancestor_label,
       n.kind, n.evidence_level
FROM up
JOIN node n ON n.node_id = up.node_id
JOIN node r ON r.node_id = up.root_id
GROUP BY up.root_id, up.node_id;

-- Which published inclusion proofs still prove membership in the current tree.
-- A route against a superseded root is not wrong; it is answering a question
-- nobody is asking any more, and it must say so rather than look like a pass.
CREATE VIEW v_route_status AS
SELECT n.label,
       r.merkle_root      AS proves_membership_in,
       COUNT(*)           AS steps,
       CASE r.is_current WHEN 1 THEN 'current' ELSE 'SUPERSEDED' END AS status
FROM merkle_route r JOIN node n USING (node_id)
GROUP BY r.node_id
ORDER BY r.is_current DESC, n.label;

-- Which sources does a given claim ultimately rest on, and how many.
CREATE VIEW v_claim_footprint AS
SELECT root_label AS claim_label,
       COUNT(*) FILTER (WHERE kind = 'SOURCE')                        AS sources,
       COUNT(*) FILTER (WHERE kind = 'SOURCE' AND evidence_level = 'RECOMPUTED') AS sources_held,
       COUNT(*) FILTER (WHERE kind = 'DERIVATION')                    AS derivations,
       MAX(depth)                                                     AS max_depth
FROM v_custody_chain
WHERE root_id IN (SELECT node_id FROM claim)
GROUP BY root_id, root_label
ORDER BY root_label;

CREATE VIEW v_fco_objects AS
SELECT fco_type, label, role, model, fco_id, object_sha256
FROM fco_object
ORDER BY fco_type, label;

CREATE VIEW v_gap_candidates AS
SELECT disease, target_symbol, drug_program, company, stage, n_trials,
       rule_fired, grade
FROM gap_candidate
ORDER BY CASE grade
  WHEN 'GAP_HIGH' THEN 1
  WHEN 'GAP_MEDIUM' THEN 2
  WHEN 'GAP_LOW' THEN 3
  WHEN 'NOT_A_GAP' THEN 4
  ELSE 5 END, disease, drug_program;

CREATE VIEW v_model_trace AS
SELECT model, family, size, status, trace_role
FROM model_trace_model
ORDER BY CASE family WHEN 'openai_api' THEN 0 ELSE 1 END, size, model;
"""


def main():
    if os.path.exists(OUT):
        os.remove(OUT)

    index = jload(STORE, "index.json")
    receipt = jload(STORE, "merkle_receipt.json")

    # leaf_index is position in the receipt's node_ids, which fcg.leaves()
    # emits in ascending node_id order. Recorded so a reader can rebuild the
    # tree from SQL alone.
    leaf_of = {nid: i for i, nid in enumerate(receipt["node_ids"])}
    leaf_hash_of = dict(zip(receipt["node_ids"], receipt["digests"]))

    con = sqlite3.connect(OUT)
    con.executescript(SCHEMA)

    # -------------------------------------------------------------- meta
    meta = [
        ("merkle_root", receipt["merkle_root"],
         "The root this database is a projection of. If it does not match "
         "fcg/store/merkle_receipt.json, this file is stale."),
        ("merkle_convention", receipt["merkle_convention"],
         "Declared, not implied. A receipt without this field is COMMITTED."),
        ("leaf_hash", receipt["leaf_hash"], None),
        ("node_hash", receipt["node_hash"], None),
        ("leaf_order", receipt["leaf_order"], None),
        ("leaf_count", str(receipt["leaf_count"]), None),
        ("generated_at", receipt["generated_at"],
         "Pinned to the observation date, not wall clock. Node ids hash node "
         "bodies, so a live clock would rename the graph on every run."),
        ("built_from", "fcg/store/",
         "This database is regenerated from the store and never edited. If "
         "the two disagree, the store is right."),
        ("claim_ceiling_science", "REPURPOSING_HYPOTHESIS", None),
        ("claim_ceiling_fto", "CLEARANCE_SEARCH_RECORD", None),
        ("not_legal_advice", "true",
         "The FTO lane is a reproducible search record. It is not an opinion."),
    ]
    con.executemany("INSERT INTO meta(key,value,note) VALUES (?,?,?)", sorted(meta))

    # -------------------------------------------------------------- nodes
    node_rows, edge_rows, src_rows, der_rows, clm_rows = [], [], [], [], []

    for entry in sorted(index["nodes"], key=lambda e: e["node_id"]):
        nid = entry["node_id"]
        rec = jload(STORE, "nodes", nid.split(":", 1)[1] + ".json")
        cust = rec.get("custody") or {}
        rcmp = rec.get("recompute") or {}
        held = 1 if cust.get("bytes_held") else 0

        node_rows.append((
            nid, rec["label"], rec["kind"], rec["layer"], rec["content_digest"],
            cust.get("bytes"), held,
            "RECOMPUTED" if held else "COMMITTED",
            rcmp.get("kind"), cust.get("origin"),
            cust.get("captured_at") or cust.get("generated_at"),
            leaf_of[nid], leaf_hash_of[nid],
            # EXACTLY the leaf preimage, byte for byte. Not a re-serialization:
            # canonical() uses ensure_ascii=False, so an em-dash is one UTF-8
            # character here and — under json.dumps' defaults. Those hash
            # differently, and a reader recomputing the leaf in another language
            # would get the wrong answer and conclude we lied.
            canonical(rec).decode("utf-8"),
        ))

        for pos, inp in enumerate(rec.get("inputs") or []):
            edge_rows.append((nid, inp, pos))

        if rec["kind"] == "SOURCE":
            src_rows.append((
                nid, cust.get("origin") or rcmp.get("uri"), cust.get("http_status"),
                cust.get("bytes"), cust.get("dataset"), cust.get("source"),
                cust.get("plate"), cust.get("plate_type"), cust.get("batch"),
                cust.get("registry"), cust.get("registry_name"), cust.get("lane"),
                cust.get("corpus_date"), cust.get("capture_method"),
                cust.get("reverify_by"),
                1 if cust.get("recomputable_offline") else 0,
                1 if cust.get("not_date_pinned") else 0,
            ))
        elif rec["kind"] == "DERIVATION":
            payload = None
            atom = rec["content_digest"].split(":", 1)[1]
            ap = os.path.join(STORE, "atoms", atom)
            if os.path.exists(ap):
                with open(ap, "rb") as fh:
                    payload = fh.read().decode("utf-8", "replace")
            der_rows.append((
                nid, rcmp.get("fn") or "?",
                json.dumps(rcmp.get("params") or {}, sort_keys=True),
                payload,
            ))
        elif rec["kind"] == "CLAIM":
            c = rec.get("claim") or {}
            ev = {}
            atom = rec["content_digest"].split(":", 1)[1]
            ap = os.path.join(STORE, "atoms", atom)
            if os.path.exists(ap):
                try:
                    with open(ap) as fh:
                        ev = json.load(fh)
                except Exception:
                    ev = {}
            body = ev.get("evidence", ev) if isinstance(ev, dict) else {}
            clm_rows.append((
                nid, c.get("statement", ""), c.get("level", ""),
                c.get("claim_ceiling", ""), c.get("hedge"),
                body.get("lane"), body.get("fto_level"),
                json.dumps(body, sort_keys=True),
            ))

    con.executemany("INSERT INTO node VALUES (" + ",".join("?" * 14) + ")", node_rows)
    con.executemany("INSERT INTO edge VALUES (?,?,?)", sorted(edge_rows))
    con.executemany("INSERT INTO source VALUES (" + ",".join("?" * 17) + ")", sorted(src_rows))
    con.executemany("INSERT INTO derivation VALUES (?,?,?,?)", sorted(der_rows))
    con.executemany("INSERT INTO claim VALUES (?,?,?,?,?,?,?,?)", sorted(clm_rows))

    # -------------------------------------------------------------- atoms
    adir = os.path.join(STORE, "atoms")
    atoms = []
    for fn in sorted(os.listdir(adir)):
        with open(os.path.join(adir, fn), "rb") as fh:
            body = fh.read()
        atoms.append(("sha256:" + fn, len(body), body))
    con.executemany("INSERT INTO atom VALUES (?,?,?)", atoms)

    # -------------------------------------------------------------- merkle
    con.executemany(
        "INSERT INTO merkle_leaf VALUES (?,?,?)",
        [(i, nid, leaf_hash_of[nid]) for nid, i in sorted(leaf_of.items(), key=lambda kv: kv[1])],
    )

    rdir = os.path.join(STORE, "routes")
    route_rows = []
    for fn in sorted(os.listdir(rdir)):
        r = jload(rdir, fn)
        cur = 1 if r["merkle_root"] == receipt["merkle_root"] else 0
        for i, step in enumerate(r["path"]):
            route_rows.append((r["node_id"], i, step["side"], step["sibling"],
                               r["merkle_root"], r.get("leaf_index"), cur))
    con.executemany("INSERT INTO merkle_route VALUES (?,?,?,?,?,?,?)", sorted(route_rows))

    # -------------------------------------------------------------- science
    import ingest as science  # noqa: E402
    con.executemany(
        "INSERT INTO consensus_gene VALUES (?,?,?,?,?,?)",
        sorted((sym, jcp, ent, well, tier, why)
               for sym, jcp, ent, well, tier, why in science.CONSENSUS),
    )

    # -------------------------------------------------------------- FTO
    rd = jload(REPO, "fto", "registry_digests.json")
    corpus_date = rd["captured_on"]
    rq = []
    for reg in rd["registries"]:
        for q in reg.get("queries", []):
            label = q.get("label") or f"opentargets_{q['gene']}"
            rq.append((
                reg["registry"], label, reg.get("endpoint"), q.get("http_status"),
                q.get("bytes"), q["sha256"], q.get("result_count"), corpus_date,
                json.dumps(q.get("params") or {}, sort_keys=True),
                q.get("gene"), q.get("ensembl"),
                q.get("sm_tractability_buckets"),
                q.get("drug_and_clinical_candidates"),
                q.get("associated_diseases"),
            ))
    # The positive control belongs in the same table as the zeros it validates.
    pc = next(r for r in rd["registries"] if r["registry"] == "open_targets")["positive_control"]
    rq.append((
        "open_targets", "opentargets_EGFR_positive_control",
        "https://api.platform.opentargets.org/api/v4/graphql", 200, None,
        "sha256:(positive control, recorded from the same query shape)", 1,
        corpus_date, json.dumps({"ensemblId": pc["ensembl"]}, sort_keys=True),
        pc["gene"], pc["ensembl"], pc["sm_tractability_buckets"],
        pc["drug_and_clinical_candidates"], None,
    ))
    con.executemany("INSERT INTO registry_query VALUES (" + ",".join("?" * 14) + ")", sorted(rq))

    from fto import registry_status  # noqa: E402
    con.executemany(
        "INSERT INTO registry_status VALUES (?,?,?,?,?)",
        sorted((r["key"], r["name"], r["lane"], 1 if r["wired"] else 0, r["blocker"])
               for r in registry_status()),
    )

    # -------------------------------------------------------------- tamper
    tp = os.path.join(STORE, "tamper_test.json")
    if os.path.exists(tp):
        t = jload(tp)
        con.executemany(
            "INSERT INTO tamper_assertion VALUES (?,?)",
            sorted((k, 1 if v else 0) for k, v in t["assertions"].items()),
        )

    # -------------------------------------------------------------- FCO
    fco_dir = os.path.join(REPO, "fco", "agent_fanout")
    fco_rows, fco_edges = [], []
    latest_path = os.path.join(fco_dir, "latest.json")
    if os.path.exists(latest_path):
        latest = jload(latest_path)
        run_dir = os.path.join(REPO, latest["path"])
        if os.path.isdir(run_dir):
            for fn in sorted(os.listdir(run_dir)):
                if not fn.endswith(".fco.json") or fn == "manifest.fco.json":
                    continue
                with open(os.path.join(run_dir, fn), "rb") as fh:
                    raw = fh.read()
                rec = json.loads(raw.decode("utf-8"))
                fco_id = rec.get("fco_id") or sha256_file(os.path.join(run_dir, fn))[0]
                fco_type = rec.get("fco_type", "unknown")
                agent = rec.get("agent") or {}
                model_info = rec.get("model") or rec.get("api") or {}
                label = (
                    agent.get("agent_id")
                    or ("openai_model" if fco_type == "openai_model" else None)
                    or ("fanout_integration" if fco_type == "fanout_integration" else fn)
                )
                fco_rows.append((
                    fco_id,
                    rec.get("run_id", latest.get("run_id", "")),
                    fco_type,
                    rec.get("schema", ""),
                    label,
                    agent.get("role"),
                    model_info.get("model_requested") or rec.get("api", {}).get("model_requested"),
                    rec.get("content_digest", fco_id),
                    sha256_file(os.path.join(run_dir, fn))[0],
                    raw.decode("utf-8"),
                ))

                if fco_type == "openai_subagent_fanout":
                    fco_edges.append(("hashed_inputs", fco_id, "read_by_agent"))
                    fco_edges.append((fco_id, "dashboard_or_docs", "proposes_update"))
                elif fco_type == "openai_model":
                    fco_edges.append((fco_id, "openai_responses_api", "model_runtime"))
                elif fco_type == "fanout_integration":
                    model_id = rec.get("model_object")
                    if model_id:
                        fco_edges.append((model_id, fco_id, "used_by_integration"))
                    for aid in rec.get("agent_objects", []) or []:
                        fco_edges.append((aid, fco_id, "integrated_by"))
                    fco_edges.append((fco_id, "protein_hinge_dashboard", "updates"))
                    fco_edges.append((fco_id, "biocustody_sql_projection", "projected_into"))
            if fco_rows:
                con.executemany(
                    "INSERT INTO fco_object VALUES (" + ",".join("?" * 10) + ")",
                    sorted(fco_rows),
                )
                con.executemany("INSERT INTO fco_edge VALUES (?,?,?)", sorted(set(fco_edges)))

    # -------------------------------------------------------------- GAP
    gap_run = os.path.join(REPO, "gap", "runs", "2026-08-13")
    candidates_csv = os.path.join(gap_run, "candidates.csv")
    if os.path.exists(candidates_csv):
        import csv
        with open(candidates_csv, newline="") as fh:
            rows = list(csv.DictReader(fh))
        con.executemany(
            "INSERT INTO gap_candidate VALUES (" + ",".join("?" * 13) + ")",
            sorted(
                (
                    r["disease"], r["target_symbol"], r["target_reconcile"],
                    r.get("alias_used"), float(r.get("association_score") or 0),
                    r["drug_program"], r.get("company"), r.get("modality"),
                    r.get("stage"), r.get("prior_trials"), int(r.get("n_trials") or 0),
                    r["rule_fired"], r["grade"],
                )
                for r in rows
            ),
        )
        receipt_path = os.path.join(gap_run, "receipt.json")
        if os.path.exists(receipt_path):
            receipt_gap = jload(receipt_path)
            con.executemany(
                "INSERT INTO gap_receipt VALUES (?,?)",
                sorted((k, json.dumps(v, sort_keys=True) if isinstance(v, (dict, list)) else str(v))
                       for k, v in receipt_gap.items()),
            )

    # -------------------------------------------------------------- Trace/context
    trace_path = os.path.join(REPO, "model_trace", "model_trace.json")
    if os.path.exists(trace_path):
        trace = jload(trace_path)
        flat = {
            "schema": trace.get("schema"),
            "claim_boundary": trace.get("claim_boundary"),
            "watchtower_search": trace.get("watchtower_search"),
            "ollarma_status": (trace.get("ollarma_readiness") or {}).get("status"),
            "null_hypothesis": trace.get("null_hypothesis"),
        }
        con.executemany(
            "INSERT INTO model_trace_record VALUES (?,?)",
            sorted((k, json.dumps(v, sort_keys=True) if isinstance(v, (dict, list)) else str(v))
                   for k, v in flat.items() if v is not None),
        )
        con.executemany(
            "INSERT INTO model_trace_model VALUES (?,?,?,?,?)",
            sorted(
                (
                    m.get("model"), m.get("family"), m.get("size"),
                    m.get("status"), m.get("trace_role"),
                )
                for m in trace.get("models", [])
            ),
        )
        ctx = trace.get("hackathon_context") or {}
        con.executemany(
            "INSERT INTO hackathon_context VALUES (?,?,?,?)",
            sorted(
                (
                    item.get("item"), item.get("integration_status"),
                    item.get("demo_language"), item.get("why_it_matters"),
                )
                for item in ctx.get("useful_items", [])
            ),
        )

    con.commit()
    con.execute("VACUUM")
    con.commit()

    # ------------------------------------------------------- self-check
    # Rebuild the root from nothing but this database's own record_json
    # column. If the stored preimages are not exactly the leaf preimages, this
    # fails here rather than in someone else's verifier six weeks from now.
    rows = con.execute(
        "SELECT leaf_index, node_id, leaf_hash, record_json "
        "FROM node ORDER BY leaf_index").fetchall()
    leaves = []
    for li, nid, lh, rj in rows:
        h = _leaf_hash(rj.encode("utf-8"))
        if "sha256:" + h.hex() != lh:
            raise SystemExit(
                f"self-check FAILED: leaf {li} ({nid}) does not recompute from "
                "its stored record_json. The database is not a faithful "
                "projection and must not be published.")
        leaves.append(h)
    rebuilt = "sha256:" + merkle_root(leaves).hex()
    if rebuilt != receipt["merkle_root"]:
        raise SystemExit(
            f"self-check FAILED: rebuilt root {rebuilt} != {receipt['merkle_root']}")
    # The static site is deployed as a folder, so it needs its own copy. Same
    # bytes, same digest — the manifest records both paths pointing at one file.
    site_copy = os.path.join(REPO, "site", "biocustody.db")
    os.makedirs(os.path.dirname(site_copy), exist_ok=True)
    with open(OUT, "rb") as a, open(site_copy, "wb") as b:
        b.write(a.read())

    verify_dump = {
        "merkle_root": receipt["merkle_root"],
        "nodes": [
            {
                "leaf_index": li,
                "node_id": nid,
                "label": label,
                "leaf_hash": lh,
                "record_json": rj,
            }
            for li, nid, label, lh, rj in con.execute(
                "SELECT m.leaf_index, n.node_id, n.label, m.leaf_hash, n.record_json "
                "FROM merkle_leaf m JOIN node n USING (node_id) "
                "ORDER BY m.leaf_index"
            )
        ],
        "routes": [
            {
                "node_id": nid,
                "label": label,
                "merkle_root": root,
                "is_current": bool(is_current),
                "path": [
                    {"side": side, "sibling": sibling}
                    for step, side, sibling in con.execute(
                        "SELECT step, side, sibling FROM merkle_route "
                        "WHERE node_id=? AND merkle_root=? ORDER BY step",
                        (nid, root),
                    )
                ],
                "record_json": rj,
            }
            for nid, label, root, is_current, rj in con.execute(
                "SELECT DISTINCT r.node_id, n.label, r.merkle_root, r.is_current, n.record_json "
                "FROM merkle_route r JOIN node n USING (node_id) "
                "ORDER BY r.is_current DESC, n.label"
            )
        ],
    }
    with open(os.path.join(REPO, "site", ".verify_dump.json"), "w") as fh:
        json.dump(verify_dump, fh, sort_keys=True)

    digest = sha256_file(OUT)
    size = os.path.getsize(OUT)

    print("=" * 74)
    print("SQLITE MATERIALIZATION")
    print("=" * 74)
    print(f"  file            {OUT}")
    print(f"  bytes           {size:,}")
    print(f"  sha256          {digest}")
    print(f"  merkle_root     {receipt['merkle_root']}")
    print(f"  self-check      root rebuilt from record_json alone: OK")
    print()
    con = sqlite3.connect(OUT)
    for tbl in ("node", "edge", "source", "derivation", "claim", "atom",
                "merkle_leaf", "merkle_route", "consensus_gene",
                "registry_query", "registry_status", "tamper_assertion",
                "fco_object", "fco_edge", "gap_candidate", "gap_receipt",
                "model_trace_record", "model_trace_model", "hackathon_context"):
        n = con.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        print(f"  {tbl:<18} {n:>5} rows")
    print()
    print("  evidence posture")
    for lvl, kind, cnt, _ in con.execute("SELECT * FROM v_evidence_posture"):
        print(f"    {lvl:<12} {kind:<12} {cnt:>3}")
    con.close()
    return digest


if __name__ == "__main__":
    main()
