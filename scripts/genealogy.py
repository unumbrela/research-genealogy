#!/usr/bin/env python3
"""One command: research direction -> a draft lineage.json, edges already real.

This automates the deterministic parts of the workflow so Claude only has to
refine. It runs the multi-pass search (anchor + frontier), selects load-bearing
nodes spanning the timeline, and — crucially — derives the `builds-on` edges
straight from the real citation graph (paper B references paper A  =>  A → B).
Edges built this way are real by construction, so they verify ✓.

What it leaves for Claude to polish: the one-line `problem` / `contribution`
(seeded from the real abstract) and any `parallel` / `inspired-by` relabeling.

Usage:
  python3 scripts/genealogy.py "<direction>" [--nodes 12] [--out lineage.json]
                                             [--render] [--source openalex|s2]

Example:
  python3 scripts/genealogy.py "contrastive learning" --nodes 12 --render
"""
import argparse
import datetime
import json
import re
import subprocess
import sys
import os

import papers

THIS = os.path.dirname(os.path.abspath(__file__))
NOW = datetime.date.today().year


def _slug(authors, year, taken):
    name = (authors or "anon").split(" et al.")[0]
    last = re.sub(r"[^a-zA-Z]", "", name.split()[-1]) if name.split() else "anon"
    base = f"{last.lower()}{year or ''}"
    slug, i = base, 0
    while slug in taken:
        slug = base + chr(ord("b") + i)
        i += 1
    taken.add(slug)
    return slug


def _first_sentence(abstract, limit=90):
    if not abstract:
        return ""
    s = re.split(r"(?<=[.。])\s", abstract.strip())[0]
    return s[:limit].rstrip() + ("…" if len(s) > limit else "")


def _norm_title(t):
    return re.sub(r"[^a-z0-9]", "", (t or "").lower())


def collect(direction, source, want):
    """Gather candidate papers (with referenced_works) from several passes.

    Dedups by id AND by normalized title (same paper often has two OpenAlex
    records — preprint vs published — keep the higher-cited one).
    """
    pool, by_id, by_title = [], {}, {}

    def add(items):
        for p in items or []:
            if not (p and p.get("id") and p.get("year")):
                continue
            if p["id"] in by_id:
                continue
            tkey = _norm_title(p.get("title"))
            prev = by_title.get(tkey)
            if prev is not None:  # duplicate title: keep the higher-cited record
                if (p.get("citations") or 0) > (prev.get("citations") or 0):
                    prev.update(p)
                continue
            by_id[p["id"]] = p
            if tkey:
                by_title[tkey] = p
            pool.append(p)

    if source == "openalex":
        add(papers.oa_search(direction, 40, with_abstract=True))    # broad recall
        add(papers.oa_search(direction, 25, precise=True,           # precision
                             with_abstract=True))
        add(papers.oa_search(direction, 20, from_year=NOW - 2,      # frontier
                             sort="citations", precise=True, with_abstract=True))
    else:
        # NOTE: s2 search does not return reference lists, so edges can't be
        # auto-derived; openalex is strongly preferred for the orchestrator.
        add(papers.s2_search(direction, 40, with_abstract=True))
        add(papers.s2_search(direction, 20, from_year=NOW - 2, sort="citations",
                             with_abstract=True))
    return pool


def select(pool, k):
    """Pick k nodes that span founders → hubs → frontier."""
    by_cite = sorted(pool, key=lambda p: (p.get("citations") or 0), reverse=True)
    shortlist = by_cite[: max(k * 3, 24)]
    founders = sorted(shortlist, key=lambda p: p.get("year") or 9999)[:2]
    frontier = [p for p in shortlist if (p.get("year") or 0) >= NOW - 2]
    frontier = sorted(frontier, key=lambda p: (p.get("citations") or 0),
                      reverse=True)[:3]
    chosen, ids = [], set()
    for p in founders + frontier + shortlist:   # priority order, dedup
        if p["id"] not in ids:
            ids.add(p["id"])
            chosen.append(p)
        if len(chosen) >= k:
            break
    return sorted(chosen, key=lambda p: (p.get("year") or 0))


def build(direction, chosen):
    """Assemble nodes + citation-derived edges."""
    taken = set()
    oa2slug, nodes = {}, []
    for p in chosen:
        slug = _slug(p.get("authors"), p.get("year"), taken)
        oa2slug[p["id"]] = slug
        nodes.append({
            "id": slug, "title": p.get("title"), "authors": p.get("authors"),
            "year": p.get("year"), "venue": p.get("venue") or "",
            "citations": p.get("citations"),
            "problem": "",
            "contribution": _first_sentence(p.get("abstract")),
            "url": p.get("url") or f"https://openalex.org/{p['id']}",
            "_abstract": p.get("abstract") or "",
        })
    # edges from the real citation graph, capped per node for readability
    refs = {p["id"]: set(p.get("referenced_works") or []) for p in chosen}
    cite = {p["id"]: (p.get("citations") or 0) for p in chosen}
    edges = []
    for b in chosen:
        ancestors = [a for a in chosen
                     if a["id"] != b["id"]
                     and (a.get("year") or 0) <= (b.get("year") or 0)
                     and a["id"] in refs[b["id"]]]
        ancestors.sort(key=lambda a: cite[a["id"]], reverse=True)
        for a in ancestors[:3]:                 # keep top-3 cited ancestors
            edges.append({"from": oa2slug[a["id"]], "to": oa2slug[b["id"]],
                          "relation": "builds-on"})
    return {"field": direction,
            "_source": f"draft by genealogy.py from {len(nodes)} OpenAlex nodes; "
                       "edges derived from real citation graph. Refine summaries "
                       "& relations, then verify.py.",
            "nodes": nodes, "edges": edges}


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("direction")
    ap.add_argument("--nodes", type=int, default=12)
    ap.add_argument("--out", default="lineage.json")
    ap.add_argument("--source", choices=["openalex", "s2"], default="openalex")
    ap.add_argument("--render", action="store_true")
    args = ap.parse_args()

    print(f"[1/3] searching “{args.direction}” …", file=sys.stderr)
    pool = collect(args.direction, args.source, args.nodes)
    if not pool:
        raise SystemExit("no papers found — try a different phrasing")
    print(f"      {len(pool)} candidates", file=sys.stderr)

    print(f"[2/3] selecting {args.nodes} load-bearing nodes …", file=sys.stderr)
    chosen = select(pool, args.nodes)

    print("[3/3] deriving citation edges …", file=sys.stderr)
    if args.source == "s2":
        print("      (s2 source: no reference lists -> no auto-edges; "
              "use openalex for the citation graph)", file=sys.stderr)
    data = build(args.direction, chosen)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"      wrote {args.out}: {len(data['nodes'])} nodes, "
          f"{len(data['edges'])} edges", file=sys.stderr)
    print(f"\nNext: refine summaries in {args.out}, then\n"
          f"  python3 {THIS}/verify.py {args.out} --write\n"
          f"  python3 {THIS}/render_tree.py {args.out}", file=sys.stderr)

    if args.render:
        subprocess.run([sys.executable, f"{THIS}/render_tree.py", args.out])


if __name__ == "__main__":
    main()
