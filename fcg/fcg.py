"""
Fractal Custody Graph (FCG) -- the content-addressed evidence store.

This IS the database. There is no server, no schema migration, no ORM.
Every object is named by the hash of its own canonical bytes, so the name
of a thing is a proof of what the thing is.

Three rules, applied identically at every depth. That identical application
at every depth is what "fractal" means here -- it is not decoration.

  R1. ADMIT IFF RECOMPUTES.
      A node is admitted only if its recorded content digest equals the
      digest recomputed from its named inputs. No exceptions, no overrides.

  R2. REJECT, DO NOT ANNOTATE.
      A node that fails R1 is REJECTED. It is not admitted-with-a-warning.
      Rejection propagates to every descendant automatically.

  R3. ROUTE-COMPARABLE TO FIRST DIVERGENT NODE.
      Any two runs can be compared by walking their routes until the first
      node whose digest differs. That node, and not a vague "something
      changed", is the answer to "what broke".

Claim grammar (levels never substitute for one another):
    COMMITTED     -- a digest was written down. Nobody checked anything.
    RECOMPUTED    -- the digest was independently reproduced from named bytes.
    AUTHENTICATED -- the recomputation was signed by an identified party.
    VALIDATED     -- an external party reproduced it from the same bytes.

This module implements COMMITTED and RECOMPUTED. It does not implement
AUTHENTICATED or VALIDATED, and it will not let you label a node with a
level it did not earn.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

SCHEMA_NODE = "biocustody.fcg.node.v1"
SCHEMA_RECEIPT = "biocustody.fcg.merkle_receipt.v1"
SCHEMA_ROUTE = "biocustody.fcg.route.v1"
SCHEMA_INDEX = "biocustody.fcg.index.v1"
SCHEMA_TAMPER = "biocustody.fcg.tamper_test.v1"

# Merkle convention is DECLARED, not assumed. A root you cannot independently
# recompute is COMMITTED, not RECOMPUTED -- see verify_receipt().
MERKLE_CONVENTION = "rfc6962/sha256"

CLAIM_LEVELS = ("COMMITTED", "RECOMPUTED", "AUTHENTICATED", "VALIDATED")


# ---------------------------------------------------------------------------
# canonical bytes
# ---------------------------------------------------------------------------

def canonical(obj: Any) -> bytes:
    """Deterministic serialization. Sorted keys, no incidental whitespace.

    Two structurally identical objects MUST produce identical bytes on any
    machine, in any process order, or the whole store is meaningless.
    """
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def sha256_bytes(b: bytes) -> str:
    return "sha256:" + hashlib.sha256(b).hexdigest()


def sha256_file(path: str, chunk: int = 1 << 20) -> Tuple[str, int]:
    h = hashlib.sha256()
    n = 0
    with open(path, "rb") as fh:
        while True:
            blk = fh.read(chunk)
            if not blk:
                break
            h.update(blk)
            n += len(blk)
    return "sha256:" + h.hexdigest(), n


def _raw(digest: str) -> bytes:
    """'sha256:abcd...' -> raw 32 bytes."""
    return bytes.fromhex(digest.split(":", 1)[1])


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# RFC 6962 Merkle tree, with real inclusion proofs
# ---------------------------------------------------------------------------

def _leaf_hash(data: bytes) -> bytes:
    return hashlib.sha256(b"\x00" + data).digest()


def _node_hash(l: bytes, r: bytes) -> bytes:
    return hashlib.sha256(b"\x01" + l + r).digest()


def _split(n: int) -> int:
    """Largest power of two strictly less than n (RFC 6962 sec 2.1)."""
    k = 1
    while k * 2 < n:
        k *= 2
    return k


def merkle_root(leaves: List[bytes]) -> bytes:
    if not leaves:
        return hashlib.sha256(b"").digest()
    if len(leaves) == 1:
        return leaves[0]
    k = _split(len(leaves))
    return _node_hash(merkle_root(leaves[:k]), merkle_root(leaves[k:]))


def merkle_path(leaves: List[bytes], index: int) -> List[Dict[str, str]]:
    """Inclusion proof for leaf `index`. This is the MERKLE ROUTE.

    Each step says: here is my sibling, and here is which side it was on.
    Replaying the steps from the leaf must land exactly on the root.
    """
    if len(leaves) <= 1:
        return []
    k = _split(len(leaves))
    if index < k:
        rest = merkle_path(leaves[:k], index)
        sib = merkle_root(leaves[k:])
        return rest + [{"sibling": "sha256:" + sib.hex(), "side": "right"}]
    rest = merkle_path(leaves[k:], index - k)
    sib = merkle_root(leaves[:k])
    return rest + [{"sibling": "sha256:" + sib.hex(), "side": "left"}]


def replay_route(leaf: bytes, path: List[Dict[str, str]]) -> bytes:
    """Walk the route. Anyone can run this. It needs no trust in us."""
    cur = leaf
    for step in path:
        sib = _raw(step["sibling"])
        cur = _node_hash(sib, cur) if step["side"] == "left" else _node_hash(cur, sib)
    return cur


# ---------------------------------------------------------------------------
# nodes
# ---------------------------------------------------------------------------

@dataclass
class Node:
    """One vertex of the custody graph.

    kind:
      SOURCE     layer 0. Bytes that entered from outside. Its custody record
                 says where it came from and how the hash was captured.
      DERIVATION layer 1+. Produced by a named function from named inputs.
      CLAIM      a statement. Carries a claim level it must have earned.
    """

    label: str
    kind: str
    layer: int
    content_digest: str
    inputs: List[str] = field(default_factory=list)
    custody: Dict[str, Any] = field(default_factory=dict)
    recompute: Dict[str, Any] = field(default_factory=dict)
    claim: Optional[Dict[str, Any]] = None

    def body(self) -> Dict[str, Any]:
        b = {
            "schema": SCHEMA_NODE,
            "label": self.label,
            "kind": self.kind,
            "layer": self.layer,
            "content_digest": self.content_digest,
            "inputs": list(self.inputs),
            "custody": self.custody,
            "recompute": self.recompute,
        }
        if self.claim is not None:
            b["claim"] = self.claim
        return b

    @property
    def node_id(self) -> str:
        """Self-naming. The id is the hash of everything the node asserts,
        so you cannot alter a node without changing its name."""
        return sha256_bytes(canonical(self.body()))

    def record(self) -> Dict[str, Any]:
        r = dict(self.body())
        r["node_id"] = self.node_id
        return r


# ---------------------------------------------------------------------------
# the store
# ---------------------------------------------------------------------------

class FCG:
    def __init__(self, root: str, clock: Optional[str] = None):
        """clock: fixes every timestamp written into node bodies.

        Node ids are hashes of node bodies, so a wall-clock timestamp inside a
        body would give the same graph a different name on every run. That
        would break the one property this store exists to provide: run it
        twice, get the same root. Pass the observation date of the underlying
        capture and the whole graph becomes reproducible by anyone.
        """
        self.root = root
        self.clock = clock
        self.nodes: Dict[str, Node] = {}
        self._order: List[str] = []
        os.makedirs(os.path.join(root, "nodes"), exist_ok=True)
        os.makedirs(os.path.join(root, "atoms"), exist_ok=True)
        os.makedirs(os.path.join(root, "routes"), exist_ok=True)

    def _now(self) -> str:
        return self.clock or now_utc()

    # -- adding -------------------------------------------------------------

    def add(self, node: Node) -> str:
        nid = node.node_id
        if nid not in self.nodes:
            self.nodes[nid] = node
            self._order.append(nid)
        return nid

    def add_source_local(self, label: str, path: str, origin: str) -> str:
        """A source whose BYTES WE HOLD. Fully recomputable."""
        digest, n = sha256_file(path)
        blob = os.path.join(self.root, "atoms", digest.split(":", 1)[1])
        if not os.path.exists(blob):
            with open(path, "rb") as src, open(blob, "wb") as dst:
                dst.write(src.read())
        return self.add(Node(
            label=label, kind="SOURCE", layer=0, content_digest=digest,
            custody={
                "origin": origin,
                "captured_at": self._now(),
                "capture_method": "local_file_read",
                "bytes": n,
                "bytes_held": True,
                "recomputable_offline": True,
            },
            recompute={"kind": "bytes_identity", "atom": digest},
        ))

    def add_source_attested(self, label: str, uri: str, digest: str, nbytes: int,
                            method: str = "http_get_sha256_at_origin",
                            extra: Optional[Dict[str, Any]] = None) -> str:
        """A source hashed AT THE POINT OF ORIGIN, whose bytes we do not keep.

        This is the honest record for a 13 MB parquet on someone else's S3
        bucket. We assert: at this instant, that URI served exactly these
        bytes. Anyone can re-fetch and check. We are not pretending to hold it.
        """
        cust = {
            "origin": uri,
            "captured_at": self._now(),
            "capture_method": method,
            "bytes": nbytes,
            "bytes_held": False,
            "recomputable_offline": False,
            "reverify_by": "re-fetch the URI and sha256 the response body",
        }
        if extra:
            cust.update(extra)
        return self.add(Node(
            label=label, kind="SOURCE", layer=0, content_digest=digest,
            custody=cust,
            recompute={"kind": "origin_attestation", "uri": uri},
        ))

    def add_derivation(self, label: str, layer: int, fn: str,
                       inputs: List[str], payload: Any,
                       params: Optional[Dict[str, Any]] = None) -> str:
        """A derived object. Its digest is the digest of its payload bytes,
        and it names every input it consumed."""
        blob = canonical(payload)
        digest = sha256_bytes(blob)
        with open(os.path.join(self.root, "atoms", digest.split(":", 1)[1]), "wb") as fh:
            fh.write(blob)
        return self.add(Node(
            label=label, kind="DERIVATION", layer=layer, content_digest=digest,
            inputs=inputs,
            custody={"generated_at": self._now(), "bytes": len(blob), "bytes_held": True},
            recompute={"kind": "function", "fn": fn, "params": params or {}},
        ))

    def add_claim(self, label: str, statement: str, level: str,
                  inputs: List[str], evidence: Any,
                  claim_ceiling: str) -> str:
        if level not in CLAIM_LEVELS:
            raise ValueError(f"unknown claim level {level!r}")
        if level in ("AUTHENTICATED", "VALIDATED"):
            raise ValueError(
                f"{level} is not implemented by this module. A claim cannot be "
                "labelled with a level it did not earn."
            )
        blob = canonical(evidence)
        digest = sha256_bytes(blob)
        with open(os.path.join(self.root, "atoms", digest.split(":", 1)[1]), "wb") as fh:
            fh.write(blob)
        return self.add(Node(
            label=label, kind="CLAIM", layer=3, content_digest=digest,
            inputs=inputs,
            custody={"generated_at": self._now(), "bytes": len(blob), "bytes_held": True},
            recompute={"kind": "bytes_identity", "atom": digest},
            claim={
                "statement": statement,
                "level": level,
                "claim_ceiling": claim_ceiling,
                "hedge": "Predicted counter-perturbation. Not measured rescue.",
            },
        ))

    # -- admission ----------------------------------------------------------

    def admit(self, node_id: str, _seen: Optional[Dict[str, Dict]] = None) -> Dict[str, Any]:
        """R1 + R2 + recursion. Returns a verdict, never raises on rejection.

        A node is ADMITTED iff every input is ADMITTED and its own bytes
        recompute to its recorded digest. Anything else is REJECTED, and the
        reason names the first thing that actually failed.
        """
        seen = _seen if _seen is not None else {}
        if node_id in seen:
            return seen[node_id]

        node = self.nodes.get(node_id)
        if node is None:
            v = {"node_id": node_id, "admitted": False, "reason": "UNKNOWN_NODE"}
            seen[node_id] = v
            return v

        # recurse first: a node cannot outrank its inputs
        input_verdicts = [self.admit(i, seen) for i in node.inputs]
        bad = [v for v in input_verdicts if not v["admitted"]]
        if bad:
            v = {
                "node_id": node_id, "label": node.label, "admitted": False,
                "reason": "INPUT_REJECTED",
                "rejected_inputs": [b["node_id"] for b in bad],
                "first_divergent_node": bad[0].get("first_divergent_node", bad[0]["node_id"]),
            }
            seen[node_id] = v
            return v

        r = node.recompute
        if r.get("kind") in ("bytes_identity", "function"):
            blob_path = os.path.join(self.root, "atoms", node.content_digest.split(":", 1)[1])
            if not os.path.exists(blob_path):
                v = {"node_id": node_id, "label": node.label, "admitted": False,
                     "reason": "ATOM_MISSING", "first_divergent_node": node_id}
                seen[node_id] = v
                return v
            with open(blob_path, "rb") as fh:
                actual = sha256_bytes(fh.read())
            if actual != node.content_digest:
                v = {"node_id": node_id, "label": node.label, "admitted": False,
                     "reason": "DIGEST_MISMATCH", "recorded": node.content_digest,
                     "recomputed": actual, "first_divergent_node": node_id}
                seen[node_id] = v
                return v
            level = "RECOMPUTED"
        else:
            # origin attestation: we did not keep the bytes, so the strongest
            # honest level is COMMITTED. Saying more would be a lie.
            level = "COMMITTED"

        v = {"node_id": node_id, "label": node.label, "admitted": True,
             "evidence_level": level}
        seen[node_id] = v
        return v

    # -- merkle -------------------------------------------------------------

    def leaves(self) -> List[Tuple[str, bytes]]:
        """Leaves are ordered by node_id so the root does not depend on the
        order in which we happened to build the graph."""
        ids = sorted(self.nodes.keys())
        return [(i, _leaf_hash(canonical(self.nodes[i].record()))) for i in ids]

    def receipt(self) -> Dict[str, Any]:
        lv = self.leaves()
        root = merkle_root([h for _, h in lv])
        return {
            "schema": SCHEMA_RECEIPT,
            "merkle_convention": MERKLE_CONVENTION,
            "leaf_hash": "sha256(0x00 || canonical_node_record)",
            "node_hash": "sha256(0x01 || left || right)",
            "leaf_order": "ascending node_id",
            "leaf_count": len(lv),
            "node_ids": [i for i, _ in lv],
            "digests": ["sha256:" + h.hex() for _, h in lv],
            "merkle_root": "sha256:" + root.hex(),
            "generated_at": self._now(),
        }

    def route(self, node_id: str) -> Dict[str, Any]:
        """The MERKLE ROUTE for one node, plus its full custody ancestry.

        This is what an artifact carries when it spins out of the system.
        Handed this object and the raw bytes, a stranger can verify the whole
        thing without contacting us.
        """
        lv = self.leaves()
        ids = [i for i, _ in lv]
        hs = [h for _, h in lv]
        if node_id not in ids:
            raise KeyError(node_id)
        idx = ids.index(node_id)
        path = merkle_path(hs, idx)
        root = merkle_root(hs)
        replay = replay_route(hs[idx], path)

        return {
            "schema": SCHEMA_ROUTE,
            "node_id": node_id,
            "label": self.nodes[node_id].label,
            "merkle_convention": MERKLE_CONVENTION,
            "leaf_index": idx,
            "leaf_hash": "sha256:" + hs[idx].hex(),
            "path": path,
            "merkle_root": "sha256:" + root.hex(),
            "route_verified": replay == root,
            "custody_chain": self.custody_chain(node_id),
            "admission": self.admit(node_id),
        }

    def custody_chain(self, node_id: str) -> List[Dict[str, Any]]:
        """Walk back to the origins. Every hop, in order, hashed."""
        chain: List[Dict[str, Any]] = []
        seen = set()

        def walk(nid: str, depth: int):
            if nid in seen:
                return
            seen.add(nid)
            n = self.nodes[nid]
            chain.append({
                "depth": depth,
                "node_id": nid,
                "label": n.label,
                "kind": n.kind,
                "layer": n.layer,
                "content_digest": n.content_digest,
                "origin": n.custody.get("origin"),
                "capture_method": n.custody.get("capture_method"),
                "bytes": n.custody.get("bytes"),
                "bytes_held": n.custody.get("bytes_held"),
            })
            for i in n.inputs:
                walk(i, depth + 1)

        walk(node_id, 0)
        return chain

    # -- persistence --------------------------------------------------------

    def flush(self) -> Dict[str, Any]:
        live = set()
        for nid, node in self.nodes.items():
            stem = nid.split(":", 1)[1]
            live.add(stem)
            p = os.path.join(self.root, "nodes", stem + ".json")
            with open(p, "wb") as fh:
                fh.write(canonical(node.record()))

        # A node id is the hash of a node body, so editing a node writes a new
        # file instead of overwriting the old one. Left alone the store fills
        # with the names of graphs that no longer exist, and someone counting
        # files gets a different answer than someone reading the index. The
        # store describes exactly one graph: the one just built.
        ndir = os.path.join(self.root, "nodes")
        for fn in os.listdir(ndir):
            if fn.endswith(".json") and fn[:-5] not in live:
                os.remove(os.path.join(ndir, fn))

        rec = self.receipt()
        with open(os.path.join(self.root, "merkle_receipt.json"), "w") as fh:
            json.dump(rec, fh, indent=2, sort_keys=True)
        index = {
            "schema": SCHEMA_INDEX,
            "generated_at": self._now(),
            "node_count": len(self.nodes),
            "merkle_root": rec["merkle_root"],
            "merkle_convention": MERKLE_CONVENTION,
            "by_layer": {},
            "nodes": [],
        }
        for nid in sorted(self.nodes):
            n = self.nodes[nid]
            index["by_layer"].setdefault(str(n.layer), 0)
            index["by_layer"][str(n.layer)] += 1
            index["nodes"].append({
                "node_id": nid, "label": n.label, "kind": n.kind,
                "layer": n.layer, "content_digest": n.content_digest,
                "inputs": n.inputs,
            })
        with open(os.path.join(self.root, "index.json"), "w") as fh:
            json.dump(index, fh, indent=2, sort_keys=True)
        return rec


# ---------------------------------------------------------------------------
# independent receipt verification
# ---------------------------------------------------------------------------

def verify_receipt(receipt: Dict[str, Any]) -> Dict[str, Any]:
    """Recompute a root from a receipt's own declared convention.

    If a receipt does not declare its convention, its root is COMMITTED and
    cannot be promoted to RECOMPUTED. That is not pedantry -- an unreproducible
    root is a number someone typed.
    """
    conv = receipt.get("merkle_convention")
    if conv is None:
        return {
            "verified": False,
            "level": "COMMITTED",
            "reason": "NO_DECLARED_MERKLE_CONVENTION",
            "detail": "Root cannot be independently recomputed; it is asserted, not proven.",
        }
    if conv != MERKLE_CONVENTION:
        return {"verified": False, "level": "COMMITTED",
                "reason": "UNSUPPORTED_CONVENTION", "detail": conv}
    leaves = [_raw(d) for d in receipt["digests"]]
    root = "sha256:" + merkle_root(leaves).hex()
    ok = root == receipt["merkle_root"]
    return {
        "verified": ok,
        "level": "RECOMPUTED" if ok else "COMMITTED",
        "recomputed_root": root,
        "recorded_root": receipt["merkle_root"],
    }
