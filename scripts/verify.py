#!/usr/bin/env python3
"""Verify the citation edges of a lineage.json against real OpenAlex data.

For every `builds-on` / `inspired-by` / `supersedes` edge A → B we expect the
later paper B to actually *cite* A. This script resolves each node to its
OpenAlex work, pulls B's reference list, and checks whether A is really in it —
turning asserted lineage into *verifiable* lineage. This is the feature that
separates the genealogy from an LLM that may hallucinate citations.

Statuses:
  ✓ verified    B cites A (edge is real)
  ⚠ unverified  no citation found either way in OpenAlex (data gap or wrong link)
  ↺ reversed    A cites B instead — the edge direction is probably backwards
  ∥ parallel    relation=parallel and neither cites the other (as expected)
  ‼ cross-cite  relation=parallel but one *does* cite the other (consider builds-on)
  ? unresolved  a node could not be matched to an OpenAlex work

Usage:
  python3 scripts/verify.py lineage.json            # print a report
  python3 scripts/verify.py lineage.json --write     # also annotate edges in-place
"""
import argparse
import json
import re
import sys

import papers  # same scripts/ dir — reuse the OpenAlex client

CITES_REL = ("builds-on", "inspired-by", "supersedes")
WID = re.compile(r"W\d+")


def resolve(node):
    """Return (openalex_id, set_of_referenced_work_ids) for a lineage node."""
    ident = None
    for field in (node.get("oa", ""), node.get("url", ""), node.get("id", "")):
        m = WID.search(field or "")
        if m:
            ident = m.group(0)
            break
    if not ident and node.get("doi"):
        ident = f"doi:{node['doi']}"
    elif not ident and node.get("arxiv"):
        ident = f"arxiv:{node['arxiv']}"
    if not ident:  # last resort: title search
        hits = papers.oa_search(node.get("title", ""), 1)
        if hits and hits[0]:
            return hits[0]["id"], set(hits[0].get("referenced_works") or [])
        return None, set()

    url = (f"{papers.OA}/works/{ident}?"
           + papers.urllib.parse.urlencode(papers._oa_params(
               {"select": "id,referenced_works"})))
    w = papers._http_json(url)
    if not w:
        return None, set()
    oaid = (w.get("id") or "").replace("https://openalex.org/", "")
    refs = {r.replace("https://openalex.org/", "")
            for r in (w.get("referenced_works") or [])}
    return oaid, refs


SYMBOL = {"verified": "✓", "unverified": "⚠", "reversed": "↺",
          "parallel": "∥", "cross-cite": "‼", "unresolved": "?"}


def verify(data):
    nodes = {n["id"]: n for n in data.get("nodes", [])}
    cache = {}

    def info(nid):
        if nid not in cache:
            print(f"  resolving {nid} …", file=sys.stderr)
            cache[nid] = resolve(nodes[nid]) if nid in nodes else (None, set())
        return cache[nid]

    results = []
    for e in data.get("edges", []):
        f, t, rel = e["from"], e["to"], e.get("relation", "builds-on")
        if f not in nodes or t not in nodes:
            results.append((e, "unresolved"))
            continue
        f_id, f_refs = info(f)
        t_id, t_refs = info(t)
        if not f_id or not t_id:
            status = "unresolved"
        elif rel in CITES_REL:
            if f_id in t_refs:
                status = "verified"
            elif t_id in f_refs:
                status = "reversed"
            else:
                status = "unverified"
        else:  # parallel
            status = "cross-cite" if (f_id in t_refs or t_id in f_refs) \
                else "parallel"
        results.append((e, status))
    return nodes, results


def report(nodes, results):
    def label(nid):
        n = nodes.get(nid, {})
        return f"{n.get('authors', nid)} {n.get('year', '')}".strip()

    counts = {}
    print()
    for e, status in results:
        counts[status] = counts.get(status, 0) + 1
        sym = SYMBOL.get(status, "?")
        rel = e.get("relation", "builds-on")
        print(f"  {sym} {status:<11} {label(e['from']):<26} "
              f"--{rel}-->  {label(e['to'])}")
    print()
    summary = "  ".join(f"{SYMBOL.get(k, '?')} {k}:{v}"
                        for k, v in sorted(counts.items()))
    print("  " + summary)
    bad = counts.get("unverified", 0) + counts.get("reversed", 0) \
        + counts.get("cross-cite", 0)
    if bad:
        print(f"\n  → {bad} edge(s) need review "
              f"(unverified / reversed / cross-cite).")
    else:
        print("\n  → all citation edges verified against OpenAlex. ✓")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lineage")
    ap.add_argument("--write", action="store_true",
                    help="annotate each edge with its verification status")
    args = ap.parse_args()

    try:
        with open(args.lineage, encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        raise SystemExit(f"cannot read {args.lineage}: {e}")

    nodes, results = verify(data)
    report(nodes, results)

    if args.write:
        for e, status in results:
            e["verified"] = status
        with open(args.lineage, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"\n  wrote verification status into {args.lineage}")


if __name__ == "__main__":
    main()
