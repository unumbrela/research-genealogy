#!/usr/bin/env python3
"""One command: research direction -> a draft lineage.json whose genealogy is
derived from the real citation graph.

Pipeline (OpenAlex metadata only — nothing recalled from memory):

  1. seed search      multi-pass keywords: broad relevance + precise +
                      frontier (recent, both most-cited and newest)
  2. snowball         pull the references + citing works of the top seed hubs,
                      so landmark papers the keywords missed still enter the
                      pool (with an on-topic filter so generic mega-cited
                      papers like backbones/optimizers stay out)
  3. in-field scoring rank candidates by citations *within the pool* — a paper
                      that everyone in the field cites is a true landmark,
                      whatever its global count
  4. selection        era-stratified: founders + hubs/bridges + frontier, with
                      a per-era cap and a bias toward nodes that actually link
                      into the rest (fewer orphans)
  5. edge derivation  "B cites A" => A --builds-on--> B, then:
                        · transitive reduction (drop A→C when A→B→C exists —
                          this is what turns a star into a readable lineage)
                        · parents = nearest predecessors (most recent first),
                          capped at 3 per node
                        · parallel detection: same-era pairs with no citation
                          path but heavy shared references => ∥ parallel

Edges come straight from reference lists, so they are real citations by
construction and are written with "verified": "verified" (parallel pairs get
"parallel"). verify.py can still re-check anything you edit by hand.

Usage:
  python3 scripts/genealogy.py "<direction>" [--nodes 12] [--out lineage.json]
      [--render] [--no-expand] [--from-year Y] [--to-year Y]

Tip: phrase <direction> in English — OpenAlex indexes English metadata.
"""
import argparse
import datetime
import json
import math
import os
import re
import subprocess
import sys
from collections import Counter

import papers

THIS = os.path.dirname(os.path.abspath(__file__))
NOW = datetime.date.today().year

STOP = frozenset("""a an and are as at be by can for from has have how in into
is it its like more most new not of on or our that the their these this those
to via we what when which with without using use used towards toward novel
based approach approaches method methods model models framework learning deep
neural network networks paper propose proposed present study results show
recent task tasks performance state art""".split())


# --------------------------------------------------------------- text utils --
def _stem(w):
    for suf in ("ization", "isation", "ations", "ation", "ions", "ing",
                "ies", "ion", "es", "ed", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 4:
            return w[: len(w) - len(suf)]
    return w


def _terms(text):
    # hyphens split ("AI-generated" -> ai, generated) so phrasing variants match
    return [_stem(w) for w in re.findall(r"[a-z][a-z0-9]+", (text or "").lower())
            if w not in STOP]


def _norm_title(t):
    return re.sub(r"[^a-z0-9]", "", (t or "").lower())


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
    parts = re.split(r"(?<=[.。])\s+", abstract.strip())
    s = ""
    for seg in parts:                    # don't break on e.g. / i.e. / et al.
        s = f"{s} {seg}".strip()
        if not re.search(r"\b(e\.g\.|i\.e\.|et al\.|vs\.|etc\.|cf\.)$", s):
            break
    return s[:limit].rstrip() + ("…" if len(s) > limit else "")


def _node_terms(p):
    return set(_terms(f"{p.get('title') or ''} {p.get('abstract') or ''}"))


def _is_survey(p):
    return bool(re.search(r"\b(survey|review|overview|advances|challenges)\b",
                          p.get("title") or "", re.I))


def field_vocab(seeds, qterms, top=40):
    """The field's own vocabulary: terms that recur across the seed papers."""
    df = Counter()
    for p in seeds:
        df.update(_node_terms(p))
    vocab = {w for w, c in df.most_common(top) if c >= 3}
    return vocab | qterms


def on_topic(p, qsets, vocab):
    """Filter for snowball-found candidates: keeps field papers, rejects
    generic mega-cited dependencies (backbones, optimizers, datasets).
    `qsets` is a list of term-sets, one per query phrasing — matching ANY
    phrasing counts (a field is often named several ways)."""
    t = _node_terms(p)
    for q in qsets:
        if q and len(t & q) >= min(2, len(q)):
            return True
    return len(t & vocab) >= 6  # non-English query: rely on seed vocabulary


def strongly_on_topic(p, qsets):
    """Hub-grade topical match: every term of some query phrasing present
    (or found by the `precise` search pass, which requires exactly that on
    the API side)."""
    if p.get("_precise"):
        return True
    t = _node_terms(p)
    return any(q and len(t & q) >= len(q) for q in qsets)


def field_core(pool, qsets):
    """The anchor set every other relevance decision hangs off.

    Text matching alone is not enough — an off-topic paper whose abstract
    happens to contain every query term (e.g. a COVID 'AI … detection from …
    images' paper) would poison hub selection. Real field papers cite each
    other, so the core is the LARGEST connected component (by citation ties)
    of the strongly-matching papers; textual impostors sit isolated and fall
    out."""
    cand = [p for p in pool if strongly_on_topic(p, qsets)]
    if len(cand) < 3:
        return cand
    idx = {p["id"]: i for i, p in enumerate(cand)}
    parent = list(range(len(cand)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i, p in enumerate(cand):
        for r in p.get("referenced_works") or []:
            j = idx.get(r)
            if j is not None:
                parent[find(i)] = find(j)
    comps = {}
    for i, p in enumerate(cand):
        comps.setdefault(find(i), []).append(p)
    biggest = max(comps.values(), key=len)
    return biggest if len(biggest) >= 3 else cand


# ------------------------------------------------------------------ collect --
def collect(direction, aliases=(), from_year=None, to_year=None,
            expand_hubs=6):
    """Multi-pass keyword search + citation snowball, over the primary
    direction AND its alias phrasings (a field is usually named several ways —
    one query never covers all branches). Dedups by id AND by normalized title
    (preprint vs published records merge: max citations, union of reference
    lists, keep an abstract if either record has one)."""
    pool, by_id, by_title = [], {}, {}

    def add(items, via, precise=False):
        for p in items or []:
            if not (p and p.get("id") and p.get("year") and p.get("title")):
                continue
            if from_year and p["year"] < from_year:
                continue
            if to_year and p["year"] > to_year:
                continue
            tkey = _norm_title(p["title"])
            prev = by_id.get(p["id"]) or by_title.get(tkey)
            if prev is not None:
                refs = set(prev.get("referenced_works") or []) \
                    | set(p.get("referenced_works") or [])
                if (p.get("citations") or 0) > (prev.get("citations") or 0):
                    via_kw = "kw" in (prev.get("_via"), via)
                    abstract = prev.get("abstract")
                    was_precise = prev.get("_precise") or precise
                    prev.update(p)
                    prev["_via"] = "kw" if via_kw else via
                    prev["_precise"] = was_precise
                    if not prev.get("abstract"):
                        prev["abstract"] = abstract
                prev["referenced_works"] = sorted(refs)
                prev["_precise"] = prev.get("_precise") or precise
                by_id[p["id"]] = prev
                continue
            p["_via"], p["_precise"] = via, precise
            by_id[p["id"]] = p
            if tkey:
                by_title[tkey] = p
            pool.append(p)

    # pass 1 — keyword seeds (broad recall, precision, frontier x2), repeated
    # for every phrasing; the primary query gets the deepest passes
    queries = [direction] + [a for a in aliases if a]
    fy = max(NOW - 2, from_year or 0)
    for i, q in enumerate(queries):
        first = (i == 0)
        n_precise = 0
        add(papers.oa_search(q, 40 if first else 20, from_year=from_year,
                             to_year=to_year, with_abstract=True), "kw")
        hits = papers.oa_search(q, 25 if first else 15, from_year=from_year,
                                to_year=to_year, precise=True,
                                with_abstract=True)
        n_precise = len(hits or [])
        add(hits, "kw", precise=True)
        add(papers.oa_search(q, 15 if first else 10, from_year=fy,
                             to_year=to_year, sort="citations", precise=True,
                             with_abstract=True), "kw", precise=True)
        add(papers.oa_search(q, 10 if first else 8,
                             from_year=max(NOW - 1, from_year or 0),
                             to_year=to_year, sort="recent", precise=True,
                             with_abstract=True), "kw", precise=True)
        print(f"      “{q}”: {n_precise} precise hits", file=sys.stderr)
    _fix_dup_years(pool, by_id)
    seeds = list(pool)
    qsets = [set(_terms(q)) for q in queries]
    vocab = field_vocab(seeds, set().union(*qsets) if qsets else set())
    core = field_core(seeds, qsets)
    print(f"      core: {len(core)} mutually-citing on-topic papers"
          + ("  ⚠ thin core — consider different phrasings"
             if len(core) < 5 else ""), file=sys.stderr)
    if not seeds or not expand_hubs:
        return _topic_gate(pool, core, qsets, vocab)

    # pass 2 — snowball, but ONLY from core hubs: picking hubs by raw global
    # citations (or even by text match alone) expands from tangential
    # mega-cited papers and floods the pool with generic vision/ML classics
    hubs = sorted(core, key=lambda p: p.get("citations") or 0,
                  reverse=True)[:expand_hubs]

    refc = Counter()                     # references co-cited by several hubs
    for h in hubs:
        for r in h.get("referenced_works") or []:
            refc[r] += 1
    ref_ids = [r for r, _ in refc.most_common(60) if r not in by_id]
    print(f"      snowball: {len(hubs)} hubs, {len(ref_ids)} refs to fetch …",
          file=sys.stderr)
    add([p for p in papers.oa_batch(ref_ids, with_abstract=True)
         if p.get("year") and on_topic(p, qsets, vocab)], "ref")

    for h in hubs:                       # descendants: who built on the hubs
        add([p for p in papers.oa_citers(h["id"], 12, with_abstract=True)
             if p.get("year") and on_topic(p, qsets, vocab)], "cite")
    for h in hubs[:2]:                   # and the newest building on top hubs
        add([p for p in papers.oa_citers(h["id"], 10, with_abstract=True,
                                         sort="recent")
             if p.get("year") and on_topic(p, qsets, vocab)], "cite")
    return _topic_gate(pool, core, qsets, vocab)


def _fix_dup_years(pool, by_id):
    """Data hygiene: OpenAlex sometimes records a classic paper with a recent
    (wrong) publication year — e.g. 'Attention Is All You Need' dated 2025 by
    an anthology reprint. A paper 'published last year' with hundreds of
    citations is suspect: try an earlier same-title OpenAlex record first,
    else cross-check the year against Semantic Scholar (year-only fix keeps
    the OpenAlex id, so the citation graph stays intact)."""
    checked = 0
    for p in list(pool):
        if not (p.get("year", 0) >= NOW - 1
                and (p.get("citations") or 0) >= 100) or checked >= 6:
            continue
        checked += 1
        tkey = _norm_title(p["title"])
        cands = [h for h in papers.oa_search(p["title"], 5, with_abstract=True)
                 if h and h.get("id") != p["id"]
                 and _norm_title(h.get("title")) == tkey
                 and (h.get("year") or 9999) < p["year"]]
        if cands:
            h = max(cands, key=lambda c: c.get("citations") or 0)
            if h["id"] in by_id:          # canonical record already pooled
                pool.remove(p)
            else:
                print(f"      fixed dup record: “{p['title'][:50]}” "
                      f"{p['year']} -> {h['year']}", file=sys.stderr)
                del by_id[p["id"]]
                p.update(h)
                by_id[p["id"]] = p
            continue
        # the OpenAlex record itself may carry a wrong (reprint) year: an old
        # paper has citers far older than its claimed publication year. Use
        # the 3rd-oldest citer so 1–2 misdated citers can't trigger a fix.
        old = sorted(c["year"] for c in
                     papers.oa_citers(p["id"], 5, sort="oldest")
                     if c and c.get("year"))
        if len(old) >= 3 and old[2] <= p["year"] - 3:
            print(f"      fixed year via earliest citers: "
                  f"“{p['title'][:50]}” {p['year']} -> {old[2]}",
                  file=sys.stderr)
            p["year"] = old[2]


def _topic_gate(pool, core, qsets, vocab):
    """Final relevance gate before scoring: keep a paper only if it belongs to
    the core, or matches the topic loosely AND has a real citation tie to the
    core. Text-only matches with no tie (an off-topic paper that happens to
    use the query words) fall out here."""
    if len(core) < 3:
        return pool                       # core too thin to anchor the gate
    core_ids = {p["id"] for p in core}
    core_refs = set()
    for p in core:
        core_refs.update(p.get("referenced_works") or [])

    def tied(p):
        return (p["id"] in core_refs
                or set(p.get("referenced_works") or []) & core_ids)

    # generic giants (backbones, base datasets) loosely match the topic words
    # and ARE cited by the core — but their citation count dwarfs the field's
    cmax = max((p.get("citations") or 0) for p in core)
    kept = [p for p in pool
            if p["id"] in core_ids
            or (on_topic(p, qsets, vocab) and tied(p)
                and (p.get("citations") or 0) <= 30 * max(cmax, 100))]
    dropped = len(pool) - len(kept)
    if dropped:
        print(f"      topic gate: dropped {dropped} off-topic candidates",
              file=sys.stderr)
    return kept


# -------------------------------------------------------------------- score --
def score_pool(pool):
    """In-field influence: citations *within the pool* beat raw global counts
    for finding the lineage's load-bearing nodes."""
    ids = {p["id"] for p in pool}
    cited = {pid: 0 for pid in ids}
    for p in pool:
        inrefs = set(p.get("referenced_works") or []) & ids
        p["_in_cites"] = len(inrefs)         # how many pool papers it builds on
        for r in inrefs:
            cited[r] += 1
    for p in pool:
        p["_in_cited"] = cited[p["id"]]      # how many pool papers cite it
        p["_score"] = (3 * p["_in_cited"] + p["_in_cites"]
                       + math.log10((p.get("citations") or 0) + 1))


# ------------------------------------------------------------------- select --
def select(pool, k):
    """Era-stratified pick: founders + frontier reserved, the rest by in-field
    score with a per-era cap and a bias toward connected nodes.

    Selection happens inside the *linked* sub-pool — papers with at least one
    citation tie to the rest. Keyword noise (old tangential papers that nothing
    in the field cites) has zero links and never makes it in."""
    pool = [p for p in pool if p.get("year")]
    linked_pool = [p for p in pool if p["_in_cited"] + p["_in_cites"] >= 1] \
        or pool
    if not pool:
        return []
    # eras from quantiles of the DISTINCT years in the linked pool: the min–max
    # span lets one early outlier skew everything, while raw-paper quantiles
    # collapse onto the recent years (the pool is recency-heavy) — distinct
    # years resist both
    years = sorted({p["year"] for p in linked_pool})

    def q(f):
        return years[min(len(years) - 1, int(f * len(years)))]

    y1 = max(p["year"] for p in linked_pool)
    cuts = (q(0.25), q(0.5), q(0.75))
    chosen, ids = [], set()

    def take(p):
        if p["id"] not in ids:
            ids.add(p["id"])
            chosen.append(p)
            return 1
        return 0

    def linked(p):
        prefs = set(p.get("referenced_works") or [])
        return any(c["id"] in prefs
                   or p["id"] in (c.get("referenced_works") or [])
                   for c in chosen)

    # founders — earliest era, must actually be cited by the field
    early = sorted((p for p in linked_pool
                    if p["year"] <= cuts[0] and p["_in_cited"] >= 1),
                   key=lambda p: (p["_in_cited"], p.get("citations") or 0),
                   reverse=True)
    for p in early[:2]:
        take(p)

    # frontier — last ~2 years, must build on the pool (or be a precise hit).
    # Method papers outrank surveys: a frontier slot should show where the
    # field is GOING, and one survey is plenty
    nf, got = (3 if k >= 12 else 2), 0
    frontier = sorted((p for p in pool if p["year"] >= max(y1 - 1, NOW - 2)),
                      key=lambda p: (not _is_survey(p),
                                     (p.get("citations") or 0)
                                     + 5 * p["_in_cites"]), reverse=True)
    for p in frontier:
        if got >= nf:
            break
        if _is_survey(p) and any(_is_survey(c) for c in chosen):
            continue
        if p["_in_cites"] >= 1 or (p.get("_precise") and p["_in_cited"] >= 1):
            got += take(p)

    # trunk — by in-field score, era-balanced; prefer connected candidates
    cap = max(2, math.ceil(k / 3))

    def bucket(p):
        return sum(1 for c in cuts if p["year"] > c)

    rest = sorted(linked_pool, key=lambda p: p["_score"], reverse=True)
    for require_link in (True, False):
        for p in rest:
            if len(chosen) >= k:
                break
            if p["id"] in ids:
                continue
            if sum(1 for c in chosen if bucket(c) == bucket(p)) >= cap:
                continue
            if require_link and not linked(p):
                continue
            take(p)
        if len(chosen) >= k:
            break
    return sorted(chosen, key=lambda p: (p["year"], -(p.get("citations") or 0)))


# -------------------------------------------------------------------- edges --
def derive_edges(chosen, slug):
    """Citation-derived lineage: transitive reduction + nearest-predecessor
    parents + parallel-pair detection. Returns ready-to-render edge dicts."""
    ids = {p["id"]: p for p in chosen}
    raw = set()
    for b, pb in ids.items():
        for a in set(pb.get("referenced_works") or []) & set(ids):
            if a != b:
                raw.add((a, b))                       # b cites a  =>  a → b
    for a, b in list(raw):                            # mutual cites: keep older→newer
        if (b, a) in raw and (a, b) in raw:
            ya, yb = ids[a].get("year") or 0, ids[b].get("year") or 0
            raw.discard((a, b) if ya > yb else (b, a))

    succ = {}
    for a, b in raw:
        succ.setdefault(a, set()).add(b)

    def has_path(x, y, skip):
        """Is there a path x→…→y, optionally ignoring the direct edge skip?"""
        stack, seen = [x], set()
        while stack:
            u = stack.pop()
            for v in succ.get(u, ()):
                if (u, v) == skip:
                    continue
                if v == y:
                    return True
                if v not in seen:
                    seen.add(v)
                    stack.append(v)
        return False

    # transitive reduction: drop a→c when a→b→…→c exists
    reduced = {(a, b) for (a, b) in raw if not has_path(a, b, (a, b))}

    # parents = nearest predecessors, capped for readability
    parents = {}
    for a, b in reduced:
        parents.setdefault(b, []).append(a)
    edges = []
    for b, ps in parents.items():
        ps.sort(key=lambda a: (ids[a].get("year") or 0, ids[a]["_in_cited"]),
                reverse=True)
        for a in ps[:3]:
            edges.append({"from": slug[a], "to": slug[b],
                          "relation": "builds-on", "verified": "verified"})
    yr = {slug[pid]: (p.get("year") or 0) for pid, p in ids.items()}
    edges.sort(key=lambda e: (yr[e["to"]], yr[e["from"]]))

    # parallel pairs: same era, no citation path either way, shared references
    pairs = []
    lst = list(ids)
    for i in range(len(lst)):
        for j in range(i + 1, len(lst)):
            a, b = lst[i], lst[j]
            if abs((ids[a].get("year") or 0) - (ids[b].get("year") or 0)) > 1:
                continue
            if has_path(a, b, None) or has_path(b, a, None):
                continue
            ra = set(ids[a].get("referenced_works") or [])
            rb = set(ids[b].get("referenced_works") or [])
            inter = len(ra & rb)
            if not inter:
                continue
            jac = inter / max(1, len(ra | rb))
            if inter >= 8 or jac >= 0.12:
                pairs.append((jac + inter / 100.0, a, b))
    pairs.sort(reverse=True)
    for _, a, b in pairs[:3]:
        if (ids[b].get("year") or 0) < (ids[a].get("year") or 0):
            a, b = b, a
        edges.append({"from": slug[a], "to": slug[b],
                      "relation": "parallel", "verified": "parallel"})
    return edges


def _cand_view(p):
    """Compact candidate entry for the draft's swap pools."""
    return {"oa": p["id"], "title": p.get("title"),
            "authors": p.get("authors"), "year": p.get("year"),
            "venue": p.get("venue") or "", "citations": p.get("citations"),
            "in_pool_cites": p.get("_in_cites", 0),
            "cited_by_pool": p.get("_in_cited", 0),
            "abstract": (p.get("abstract") or "")[:240]}


# -------------------------------------------------------------------- build --
def build(direction, chosen, pool=()):
    taken, slug = set(), {}
    nodes = []
    for p in chosen:
        s = _slug(p.get("authors"), p.get("year"), taken)
        slug[p["id"]] = s
        nodes.append({
            "id": s, "oa": p["id"],     # OpenAlex work id — verify.py uses it
            "title": p.get("title"), "authors": p.get("authors"),
            "year": p.get("year"), "venue": p.get("venue") or "",
            "citations": p.get("citations"),
            "problem": "",
            "contribution": _first_sentence(p.get("abstract")),
            "url": p.get("url") or f"https://openalex.org/{p['id']}",
            "_abstract": p.get("abstract") or "",
        })
    edges = derive_edges(chosen, slug)

    # health stats so the refiner (Claude) knows what to fix
    linked = {e["from"] for e in edges} | {e["to"] for e in edges}
    has_parent = {e["to"] for e in edges if e["relation"] != "parallel"}
    orphans = [n["id"] for n in nodes if n["id"] not in linked]
    roots = [n["id"] for n in nodes if n["id"] not in has_parent
             and n["id"] in linked]
    stats = {"orphans": orphans, "roots": roots,
             "note": ("draft by genealogy.py — every builds-on edge is a real "
                      "OpenAlex citation. TODO for the refiner: rewrite each "
                      "problem/contribution from _abstract; relabel edges to "
                      "inspired-by/supersedes where appropriate; for each "
                      "orphan either find its real link (papers.py expand) or "
                      "drop it; prune off-topic nodes; consider swapping in "
                      "better nodes from _frontier_candidates/_alternates.")}

    # swap pools: strong papers that did NOT make the cut, so the refiner can
    # improve coverage (especially of the last 2 years) without re-searching
    chosen_ids = set(slug)
    rest = sorted((p for p in pool if p["id"] not in chosen_ids
                   and p.get("year")),
                  key=lambda p: p.get("_score", 0), reverse=True)
    frontier_cands = sorted((p for p in rest if p["year"] >= NOW - 2
                             and (p.get("_in_cites", 0) >= 1
                                  or p.get("_precise"))),
                            key=lambda p: ((p.get("citations") or 0)
                                           + 5 * p.get("_in_cites", 0)),
                            reverse=True)[:10]
    alternates = [p for p in rest if p not in frontier_cands][:8]
    return {"field": direction, "_stats": stats, "nodes": nodes,
            "edges": edges,
            "_frontier_candidates": [_cand_view(p) for p in frontier_cands],
            "_alternates": [_cand_view(p) for p in alternates]}


# --------------------------------------------------------------------- main --
def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("direction", help="research direction (English phrasing)")
    ap.add_argument("--alias", action="append", default=[],
                    help="extra English phrasing for the same direction; "
                         "repeatable — use for sub-branches and synonyms "
                         "(e.g. for AI4Reaction: --alias 'retrosynthesis "
                         "prediction deep learning' --alias 'reaction yield "
                         "prediction machine learning')")
    ap.add_argument("--nodes", type=int, default=12)
    ap.add_argument("--out", default="lineage.json")
    ap.add_argument("--from-year", type=int, dest="from_year")
    ap.add_argument("--to-year", type=int, dest="to_year")
    ap.add_argument("--no-expand", action="store_true",
                    help="skip the citation snowball (faster, weaker pool)")
    ap.add_argument("--render", action="store_true")
    args = ap.parse_args()

    label = " / ".join([args.direction] + args.alias) if args.alias \
        else args.direction
    print(f"[1/4] searching “{label}” …", file=sys.stderr)
    pool = collect(args.direction, args.alias, args.from_year, args.to_year,
                   expand_hubs=0 if args.no_expand else 6)
    if not pool:
        raise SystemExit("no papers found — try a different (English) phrasing")
    print(f"      {len(pool)} candidates "
          f"({sum(1 for p in pool if p.get('_via') != 'kw')} via snowball)",
          file=sys.stderr)

    print("[2/4] scoring in-field influence …", file=sys.stderr)
    score_pool(pool)

    print(f"[3/4] selecting {args.nodes} load-bearing nodes …", file=sys.stderr)
    chosen = select(pool, args.nodes)

    print("[4/4] deriving citation edges (transitive reduction) …",
          file=sys.stderr)
    data = build(args.direction, chosen, pool)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    nb = sum(1 for e in data["edges"] if e["relation"] == "builds-on")
    npar = len(data["edges"]) - nb
    st = data["_stats"]
    print(f"      wrote {args.out}: {len(data['nodes'])} nodes, "
          f"{nb} builds-on + {npar} parallel edges "
          f"(roots: {len(st['roots'])}, orphans: {len(st['orphans'])})",
          file=sys.stderr)
    if st["orphans"]:
        print(f"      ⚠ orphan nodes to link or drop: "
              f"{', '.join(st['orphans'])}", file=sys.stderr)
    print(f"\nNext: refine summaries/relations in {args.out}, then\n"
          f"  python3 {THIS}/render_tree.py {args.out}", file=sys.stderr)

    if args.render:
        subprocess.run([sys.executable, f"{THIS}/render_tree.py", args.out])


if __name__ == "__main__":
    main()
