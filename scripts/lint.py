#!/usr/bin/env python3
"""Quality gate for a refined lineage.json — run AFTER Step 2, BEFORE render.

genealogy.py produces a *draft*; the real product is the refined genealogy. The
SKILL's "Quality bar" used to be prose the human had to self-check, so a lazy or
half-finished refinement still rendered a clean-looking tree. This script turns
that prose into enforced checks: a non-zero exit means the genealogy is NOT done.

  python3 scripts/lint.py lineage.json            # gate a refined file
  python3 scripts/lint.py lineage.json --curated   # relax time-relative checks
                                                   # (for frozen example files)
  python3 scripts/lint.py lineage.json --strict    # warnings fail too

Severities:
  ✗ ERROR  blocks delivery (exit 1)
  ⚠ WARN   worth a look, doesn't block (exit 0 unless --strict)
  ✓ OK
"""
import argparse
import datetime
import json
import re
import sys

NOW = datetime.date.today().year
REL_OK = {"builds-on", "inspired-by", "parallel", "supersedes"}
CITE_REL = {"builds-on", "inspired-by", "supersedes"}      # directed lineage
SURVEY = re.compile(r"\b(survey|review|overview|advances|challenges)\b", re.I)
# draft scaffolding that should be gone from a delivered file
DRAFT_KEYS = ("_stats", "_frontier_candidates", "_alternates", "_unresolved")


class Gate:
    def __init__(self, strict=False):
        self.errors, self.warns, self.strict = [], [], strict

    def check(self, cond, msg, warn=False):
        mark = "✓" if cond else ("⚠" if warn else "✗")
        print(f"  {mark} {msg}")
        if not cond:
            (self.warns if warn else self.errors).append(msg)
        return cond

    def failed(self):
        return bool(self.errors) or (self.strict and self.warns)


def _rel(e):
    return e.get("relation", "builds-on")


def _children(edges):
    """builds-on parent->children adjacency (the lineage trunk)."""
    ch = {}
    for e in edges:
        if _rel(e) == "builds-on":
            ch.setdefault(e["from"], []).append(e["to"])
    return ch


def _deepest_chain(ids, ch):
    """Longest builds-on chain length (in edges); cycle-safe."""
    memo, stack = {}, set()

    def depth(n):
        if n in memo:
            return memo[n]
        if n in stack:                 # defensive: a cycle shouldn't exist
            return 0
        stack.add(n)
        best = max((1 + depth(c) for c in ch.get(n, [])), default=0)
        stack.discard(n)
        memo[n] = best
        return best

    return max((depth(n) for n in ids), default=0)


def lint(data, curated=False, strict=False):
    g = Gate(strict)
    nodes = data.get("nodes", [])
    edges = data.get("edges", [])
    ids = [n.get("id") for n in nodes]
    idset = set(ids)
    years = [n.get("year") for n in nodes if n.get("year")]
    print(f"[{data.get('field', '?')}] {len(nodes)} nodes, {len(edges)} edges")

    # --- structural floor (same invariants selftest guards) -----------------
    g.check(bool(data.get("field")), "has a field label")
    g.check(len(nodes) >= 5, f"≥5 nodes (got {len(nodes)})")
    g.check(all(n.get("id") and n.get("title") and n.get("year")
                for n in nodes), "every node has id/title/year")
    g.check(len(idset) == len(nodes), "node ids are unique")
    g.check(all(_rel(e) in REL_OK for e in edges),
            "every edge relation is valid")
    g.check(all(e.get("from") in idset and e.get("to") in idset
                for e in edges), "every edge connects existing nodes")

    # --- Step 2 actually completed ------------------------------------------
    blank = [n["id"] for n in nodes if not (n.get("problem") or "").strip()
             or not (n.get("contribution") or "").strip()]
    g.check(not blank, f"every node has problem + contribution{_show(blank)}")
    residue = [n["id"] for n in nodes if "_abstract" in n]
    g.check(not residue, f"no leftover _abstract draft keys{_show(residue)}")
    scaffold = [k for k in DRAFT_KEYS if k in data]
    g.check(not scaffold, f"draft scaffolding removed{_show(scaffold)}",
            warn=True)
    seed = [n["id"] for n in nodes
            if (n.get("contribution") or "").rstrip().endswith("…")]
    g.check(not seed, f"summaries rewritten (not raw abstract seeds)"
            f"{_show(seed)}", warn=True)
    hinted = [f"{e['from']}→{e['to']}" for e in edges if e.get("_label_hint")]
    g.check(not hinted, f"auto-labelled relations confirmed (_label_hint "
            f"cleared){_show(hinted)}", warn=True)

    # --- graph shape: no star, real lineage ---------------------------------
    linked = {e["from"] for e in edges} | {e["to"] for e in edges}
    orphans = [i for i in ids if i not in linked]
    g.check(not orphans, f"zero orphans{_show(orphans)}")

    ch = _children(edges)
    deepest = _deepest_chain(idset, ch)
    g.check(deepest >= 3, f"deepest builds-on chain ≥ 3 edges (got {deepest})")
    fanout = {p: len(c) for p, c in ch.items()}
    wide = [p for p, n in fanout.items() if n >= 6]
    g.check(not wide, f"no star hub (≥6 direct children){_show(wide)}")
    branch_pts = sum(1 for n in fanout.values() if n >= 2)
    g.check(branch_pts >= 1 or len(nodes) <= 5,
            f"the trunk branches (≥1 node with ≥2 children, got {branch_pts})",
            warn=True)

    rels = {_rel(e) for e in edges}
    g.check(bool(rels - {"builds-on"}),
            "≥1 non-builds-on relation (parallel / inspired-by / supersedes)")

    # --- reaches the present, with a real frontier --------------------------
    if years:
        maxy = max(years)
        if curated:
            recent = [n["id"] for n in nodes
                      if (n.get("year") or 0) >= maxy - 2]
            g.check(len(recent) >= 3,
                    f"≥3 nodes within 2 years of the file's latest "
                    f"({maxy}) — got {len(recent)}")
        else:
            g.check(maxy >= NOW - 2,
                    f"genealogy reaches the present (max year {maxy} ≥ "
                    f"{NOW - 2}) — stopping years ago is the #1 failure mode")
            recent_nodes = [n for n in nodes if (n.get("year") or 0) >= NOW - 2]
            g.check(len(recent_nodes) >= 3,
                    f"≥3 frontier nodes from the last 2 years "
                    f"(got {len(recent_nodes)})")
            n_survey = sum(1 for n in recent_nodes if SURVEY.search(
                n.get("title") or ""))
            g.check(n_survey <= 1,
                    f"frontier is methods, not a pile of surveys "
                    f"({n_survey} surveys in the last 2 years)", warn=True)

    print()
    if g.errors:
        print(f"FAILED — {len(g.errors)} error(s)"
              + (f", {len(g.warns)} warning(s)" if g.warns else "") + ":")
        for m in g.errors:
            print(f"  ✗ {m}")
        for m in g.warns:
            print(f"  ⚠ {m}")
    elif g.warns:
        print(f"PASSED with {len(g.warns)} warning(s):")
        for m in g.warns:
            print(f"  ⚠ {m}")
    else:
        print("Quality gate passed. ✓")
    return g


def _show(items):
    return "" if not items else ": " + ", ".join(map(str, items))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lineage")
    ap.add_argument("--curated", action="store_true",
                    help="relax now-relative frontier checks (frozen examples)")
    ap.add_argument("--strict", action="store_true",
                    help="treat warnings as failures too")
    args = ap.parse_args()
    with open(args.lineage, encoding="utf-8") as f:
        data = json.load(f)
    g = lint(data, curated=args.curated, strict=args.strict)
    sys.exit(1 if g.failed() else 0)


if __name__ == "__main__":
    main()
