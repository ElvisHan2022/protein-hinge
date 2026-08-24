/*
 * Headless test of the browser verifier.
 *
 * The PROVE tab claims it can rebuild the Merkle root from nothing but the
 * record bytes stored in the database. That claim is worth exactly as much as
 * the evidence for it, so this file lifts the crypto and tree code out of
 * index.html and runs it against the real database under Node.
 *
 * It runs the tree TWICE: once on WebCrypto and once on the in-page SHA-256
 * fallback. Both must produce the same root as fcg/store/merkle_receipt.json.
 * A fallback that quietly returns wrong hashes would turn "could not verify"
 * into "verified", which is the one failure mode this whole repo exists to
 * prevent.
 *
 * Run:  python3 db/build_db.py && node site/verify_test.js
 */
const fs = require('fs');
const path = require('path');

const HERE = __dirname;
const REPO = path.dirname(HERE);
// Normalised to LF: git autocrlf checks index.html out with CRLF on
// Windows, while the lift markers below are written with bare LF.
const SRC = fs.readFileSync(path.join(HERE, 'index.html'), 'utf8')
  .split('\r\n').join('\n');

// ---- lift the implementation straight out of the page ---------------------
// Deliberately not a reimplementation. If someone edits index.html and breaks
// the math, this test has to break with it.
function lift(startMarker, endMarker) {
  const a = SRC.indexOf(startMarker);
  const b = SRC.indexOf(endMarker, a);
  if (a < 0 || b < 0) throw new Error(`could not lift ${startMarker}`);
  return SRC.slice(a, b);
}
const cryptoBlock = lift('const K=[0x428a2f98', 'const HAVE_SUBTLE');
const treeBlock = lift('const hex = u8', 'async function merkleRoot');
const rootBlock = lift('async function merkleRoot', '\n\n// ------');

// treeBlock already defines hex, cat, enc, leafHash, nodeHash and split.
const ctx = {};
new Function('ctx', `
  ${cryptoBlock}
  ${treeBlock}
  ${rootBlock}
  ctx.sha256js = sha256js; ctx.hex = hex; ctx.cat = cat;
  ctx.enc = enc; ctx.split = split;
`)(ctx);
const enc = ctx.enc;

// merkleRoot closes over sha256/leafHash/nodeHash inside that scope, so build
// the tree here against whichever primitive we are testing.
function makeTree(sha256) {
  const { hex, cat, split } = ctx;
  const leafHash = async rec => sha256(cat(new Uint8Array([0]), enc.encode(rec)));
  const nodeHash = async (l, r) => sha256(cat(new Uint8Array([1]), l, r));
  async function merkleRoot(leaves) {
    if (!leaves.length) return sha256(new Uint8Array(0));
    if (leaves.length === 1) return leaves[0];
    const k = split(leaves.length);
    return nodeHash(await merkleRoot(leaves.slice(0, k)), await merkleRoot(leaves.slice(k)));
  }
  return { leafHash, nodeHash, merkleRoot, hex };
}

// ---- the data -------------------------------------------------------------
const dumpPath = path.join(HERE, '.verify_dump.json');
if (!fs.existsSync(dumpPath)) {
  console.error('missing ' + dumpPath + '\nrun: python3 db/build_db.py && node site/verify_test.js');
  process.exit(2);
}
const dump = JSON.parse(fs.readFileSync(dumpPath, 'utf8'));

const subtleSha = async b => new Uint8Array(await require('crypto').webcrypto.subtle.digest('SHA-256', b));

async function run(name, sha256) {
  const { leafHash, nodeHash, merkleRoot, hex } = makeTree(sha256);
  const leaves = [];
  let leafMismatch = 0;
  for (const r of dump.nodes) {
    const h = await leafHash(r.record_json);
    if ('sha256:' + hex(h) !== r.leaf_hash) leafMismatch++;
    leaves.push(h);
  }
  const root = 'sha256:' + hex(await merkleRoot(leaves));

  // Replay the published inclusion proofs too — the VERIFY tab depends on them.
  let routeFail = 0;
  const currentRoutes = dump.routes.filter(rt => rt.is_current !== false);
  const staleRoutes = dump.routes.length - currentRoutes.length;
  const un = h => Uint8Array.from(h.replace('sha256:', '').match(/../g).map(x => parseInt(x, 16)));
  for (const rt of currentRoutes) {
    let acc = await leafHash(rt.record_json);
    for (const s of rt.path) {
      const sib = un(s.sibling);
      acc = s.side === 'left' ? await nodeHash(sib, acc) : await nodeHash(acc, sib);
    }
    if ('sha256:' + hex(acc) !== dump.merkle_root) routeFail++;
  }

  const ok = leafMismatch === 0 && root === dump.merkle_root && routeFail === 0;
  console.log(`  ${ok ? 'PASS' : 'FAIL'}  ${name}`);
  console.log(`          leaves ${dump.nodes.length - leafMismatch}/${dump.nodes.length} recompute`);
  console.log(`          current routes ${currentRoutes.length - routeFail}/${currentRoutes.length} replay to root`);
  if (staleRoutes) console.log(`          stale routes ${staleRoutes} recorded but not replayed against current root`);
  console.log(`          root   ${root}`);
  return ok;
}

(async () => {
  console.log('browser verifier, run headless against the real database');
  console.log('expected root  ' + dump.merkle_root);
  console.log();
  const a = await run('WebCrypto path (crypto.subtle)', subtleSha);
  console.log();
  const b = await run('in-page fallback (sha256js)', async x => ctx.sha256js(x));
  console.log();

  // A tampered record must move the root. If it does not, the PROVE tab is
  // decoration and the TAMPER button proves nothing.
  const { leafHash, merkleRoot, hex } = makeTree(subtleSha);
  const tampered = dump.nodes.map(n => ({ ...n }));
  const candidates = [
    ['consensus_axis_specification', '"replicates_per_gene":7', '"replicates_per_gene":8'],
    ['counter_perturbation_ranking_method', '"layer":2', '"layer":3'],
  ];
  let t, from, to;
  for (const c of candidates) {
    t = tampered.find(n => n.label === c[0]);
    if (t && t.record_json.includes(c[1])) {
      from = c[1];
      to = c[2];
      break;
    }
  }
  if (!t || !from) throw new Error('could not find a deterministic tamper target');
  t.record_json = t.record_json.replace(from, to);
  const leaves = [];
  for (const r of tampered) leaves.push(await leafHash(r.record_json));
  const badRoot = 'sha256:' + hex(await merkleRoot(leaves));
  const moved = badRoot !== dump.merkle_root;
  console.log(`  ${moved ? 'PASS' : 'FAIL'}  one-character edit moves the root`);
  console.log(`          ${from} -> ${to} in ${t.label}`);
  console.log(`          root   ${badRoot}`);
  console.log();
  console.log(`  OVERALL  ${a && b && moved ? 'PASS' : 'FAIL'}`);
  process.exit(a && b && moved ? 0 : 1);
})();
