#!/usr/bin/env python3
"""Lightweight regression guard for the research-genealogy pipeline.

Not a unit-test suite — a smoke test that protects the *core invariants* the
verification and topic-gating logic must keep, so refactors (dup-record
reconciliation, S2 fallback, topic gate, orphan repair) can't silently break
the examples or regress draft quality.

  python3 scripts/selftest.py            # fast, offline: structural checks on examples
  python3 scripts/selftest.py --online   # also re-verify examples + run a live draft

Exit code is non-zero if any check fails (CI-friendly).
"""
import argparse
import glob
import json
import os
import subprocess
import sys

THIS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(THIS)
REL_OK = {"builds-on", "inspired-by", "parallel", "supersedes"}
# illustrative-only fixture (not real papers) — schema-checked, not verified
SYNTHETIC = {"lineage.example.json"}


class Check:
    def __init__(self):
        self.failures = []

    def ok(self, cond, msg):
        mark = "✓" if cond else "✗"
        print(f"  {mark} {msg}")
        if not cond:
            self.failures.append(msg)
        return cond


def structural(path, c):
    """Schema + graph invariants that must hold for every lineage file."""
    name = os.path.basename(path)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    nodes = data.get("nodes", [])
    edges = data.get("edges", [])
    ids = {n.get("id") for n in nodes}
    print(f"\n[{name}] {len(nodes)} nodes, {len(edges)} edges")

    c.ok(data.get("field"), "has a field label")
    c.ok(len(nodes) >= 5, "≥5 nodes")
    c.ok(all(n.get("id") and n.get("title") and n.get("year") for n in nodes),
         "every node has id/title/year")
    c.ok(len(ids) == len(nodes), "node ids are unique")
    c.ok(all(e.get("relation", "builds-on") in REL_OK for e in edges),
         "every edge relation is valid")
    c.ok(all(e["from"] in ids and e["to"] in ids for e in edges),
         "every edge connects existing nodes")

    if name not in SYNTHETIC:
        linked = {e["from"] for e in edges} | {e["to"] for e in edges}
        orphans = [n["id"] for n in nodes if n["id"] not in linked]
        c.ok(not orphans, f"no orphan nodes (curated example){_show(orphans)}")
        c.ok(all((n.get("problem") or "").strip()
                 and (n.get("contribution") or "").strip() for n in nodes),
             "every node has problem + contribution written")
    return data


def _show(items):
    return "" if not items else ": " + ", ".join(items)


def quality_gate(path, c):
    """Run the lint.py quality gate (curated mode) so the examples stay valid
    deliverables, and so refactors to the gate can't silently regress them."""
    name = os.path.basename(path)
    sys.path.insert(0, THIS)
    import importlib
    lint = importlib.import_module("lint")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    print(f"\n[{name}] quality gate")
    g = lint.lint(data, curated=True)
    c.ok(not g.errors, f"lint passes (curated){_show(g.errors)}")


def verify_ratio(path, c):
    """Re-verify a curated example against live OpenAlex/S2 and assert the
    verified ratio doesn't regress and nothing is reversed."""
    name = os.path.basename(path)
    sys.path.insert(0, THIS)
    import importlib
    verify = importlib.import_module("verify")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    _, results = verify.verify(data)
    counts = {}
    for _, status in results:
        counts[status] = counts.get(status, 0) + 1
    cite_edges = sum(1 for e, _ in results
                     if e.get("relation", "builds-on") in verify.CITES_REL)
    ver = counts.get("verified", 0)
    rev = counts.get("reversed", 0)
    ratio = ver / cite_edges if cite_edges else 1.0
    print(f"\n[{name}] verify: {counts}")
    c.ok(rev == 0, f"no reversed edges{_show([] if not rev else ['%d' % rev])}")
    c.ok(ratio >= 0.75,
         f"verified ratio {ver}/{cite_edges} = {ratio:.0%} ≥ 75%")


def resolve_smoke(c):
    """The grounding step that keeps 'Claude proposes, scripts verify'
    zero-hallucination: a real title resolves to a real record, a fabricated one
    resolves to nothing (never invented)."""
    sys.path.insert(0, THIS)
    import importlib
    papers = importlib.import_module("papers")
    print("\n[resolve] title grounding")
    real = papers.resolve_title("Denoising Diffusion Probabilistic Models")
    c.ok(bool(real and real.get("year") == 2020),
         f"real title resolves to a real record "
         f"(got {real.get('year') if real else None})")
    junk = papers.resolve_title("A Completely Fabricated Paper That Cannot Exist 9999")
    c.ok(junk is None, "fabricated title resolves to None (not invented)")


def live_draft(c):
    """Run one small live draft and assert the pipeline produces a connected,
    on-topic genealogy (orphan repair + topic gate working end to end)."""
    out = "/tmp/selftest_draft.json"
    cmd = [sys.executable, f"{THIS}/genealogy.py",
           "denoising diffusion probabilistic models image generation",
           "--alias", "latent diffusion text-to-image",
           "--nodes", "10", "--prune-orphans", "--out", out]
    print("\n[live draft] running genealogy.py …")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    log = proc.stderr
    core = next((int(l.split("core:")[1].split("mutually")[0])
                 for l in log.splitlines() if "core:" in l), 0)
    c.ok(proc.returncode == 0, "genealogy.py exits 0")
    c.ok(core >= 5, f"relevance core ≥ 5 (got {core})")
    if os.path.exists(out):
        with open(out, encoding="utf-8") as f:
            data = json.load(f)
        linked = {e["from"] for e in data["edges"]} \
            | {e["to"] for e in data["edges"]}
        orphans = [n["id"] for n in data["nodes"] if n["id"] not in linked]
        c.ok(not orphans, f"draft has no orphans after --prune-orphans"
                          f"{_show(orphans)}")
        c.ok(len(data["edges"]) >= len(data["nodes"]) - 1,
             "draft is connected enough (edges ≥ nodes-1)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--online", action="store_true",
                    help="also re-verify examples and run a live draft (network)")
    args = ap.parse_args()

    c = Check()
    for path in sorted(glob.glob(os.path.join(ROOT, "examples", "*.json"))):
        structural(path, c)
        if os.path.basename(path) not in SYNTHETIC:
            quality_gate(path, c)

    if args.online:
        for path in sorted(glob.glob(os.path.join(ROOT, "examples", "*.json"))):
            if os.path.basename(path) not in SYNTHETIC:
                verify_ratio(path, c)
        resolve_smoke(c)
        live_draft(c)

    print()
    if c.failures:
        print(f"FAILED — {len(c.failures)} check(s):")
        for m in c.failures:
            print(f"  ✗ {m}")
        sys.exit(1)
    print("All checks passed. ✓")


if __name__ == "__main__":
    main()
