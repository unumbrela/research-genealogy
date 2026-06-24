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


def _surface_terms(text):
    """Like _terms but keeps the readable surface form (no stemming), for
    composing human-readable alias phrasings."""
    return [w for w in re.findall(r"[a-z][a-z0-9\-]+", (text or "").lower())
            if w not in STOP and len(w) > 2]


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


# generative milestones that typically *inspire* a downstream analysis/detection
# wave rather than being directly extended by it
GEN_MILESTONE = re.compile(
    r"\b(gan|generative adversarial|dall[\s·.-]?e|stable diffusion|imagen|"
    r"midjourney|glide|vqgan|latent diffusion|text-to-image|"
    r"diffusion model)\b", re.I)
# explicit superiority language => the later work may *supersede* the earlier
SUPERIOR = re.compile(
    r"\b(outperform\w*|surpass\w*|state[- ]of[- ]the[- ]art|\bsota\b|"
    r"superior to|substantially improv\w+|new best)\b", re.I)


def _relabel(edges, ids, slug):
    """Draft heuristic relation labels — builds-on → inspired-by / supersedes —
    each flagged `_label_hint:"auto"` so Step 2 confirms rather than trusts.
    Deliberately high-precision / low-recall: a wrong *builds-on* default is
    cheaper than a wrong confident relabel."""
    inv = {s: pid for pid, s in slug.items()}
    terms = {pid: _node_terms(p) for pid, p in ids.items()}
    # lineage in-degree per child: builds-on/inspired-by edges keep a node in the
    # tree, supersedes does not — so we must never strip a node's last parent
    lineage_in = Counter(e["to"] for e in edges
                         if e.get("relation") in ("builds-on", "inspired-by"))
    for e in edges:
        if e.get("relation") != "builds-on":
            continue
        a, b = ids.get(inv.get(e["from"])), ids.get(inv.get(e["to"]))
        if not a or not b:
            continue
        ta, tb = terms[a["id"]], terms[b["id"]]
        jac = len(ta & tb) / max(1, len(ta | tb))
        # inspired-by: a generative milestone feeding a different sub-problem
        # (low topical overlap) — e.g. DALL·E 2 triggering a detection wave.
        # Stays a lineage relation, so the node keeps its tree parent.
        if jac < 0.10 and GEN_MILESTONE.search(a.get("title") or ""):
            e["relation"], e["_label_hint"] = "inspired-by", "auto"
            continue
        # supersedes: same problem family (high overlap) + an explicit
        # superiority claim in the later paper, year gap ≥ 1 — but only when the
        # child has another lineage parent left, so the tree stays connected.
        if (jac >= 0.18 and (b.get("year") or 0) - (a.get("year") or 0) >= 1
                and lineage_in[e["to"]] >= 2
                and SUPERIOR.search(b.get("abstract") or "")):
            e["relation"], e["_label_hint"] = "supersedes", "auto"
            lineage_in[e["to"]] -= 1


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


def _resolve_arxiv_to_oa(p):
    """Find the OpenAlex twin of an arXiv hit by exact (normalized) title, so a
    preprint the keyword passes missed still enters the citation graph with real
    references. Returns an oa_slim dict (real W-id, refs, citations) or None."""
    title = p.get("title") or ""
    if not title:
        return None
    for h in papers.oa_search(title, 3, with_abstract=True):
        if h and _norm_title(h.get("title")) == _norm_title(title):
            return h
    return None


# ------------------------------------------------------------------ collect --
def collect(direction, aliases=(), from_year=None, to_year=None,
            expand_hubs=6, seed_titles=()):
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
                if p.get("_seed"):
                    prev["_seed"] = True       # a keyword hit confirming a seed
                by_id[p["id"]] = prev
                continue
            p["_via"], p["_precise"] = via, precise
            by_id[p["id"]] = p
            if tkey:
                by_title[tkey] = p
            pool.append(p)

    # pass 0.5 — Claude-proposed seeds: resolve each title to a REAL record and
    # inject it as a trusted, on-topic pool member. This is the "Claude proposes,
    # scripts verify" path: Claude's recall (its knowledge + WebSearch) names the
    # landmarks and the newest work; resolution keeps every node grounded. A
    # title that resolves nowhere is returned in `unresolved` and never invented.
    unresolved = []
    if seed_titles:
        resolved, unresolved = papers.resolve_titles(list(seed_titles),
                                                      with_abstract=True)
        for rec in resolved:
            rec["_seed"] = True
            if rec.get("referenced_works"):
                add([rec], "seed", precise=True)   # joins the citation graph
            else:                                  # arXiv/S2-only: ref-less, so
                rec["_no_refs"] = True             # frontier candidate, not trunk
                add([rec], "arxiv")
        print(f"      seeds: {len(resolved)} resolved, {len(unresolved)} "
              f"unresolved", file=sys.stderr)

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

    # pass 1.5 — arXiv frontier: the newest preprints OpenAlex may not index yet
    # (months of lag), the direct cause of genealogies that "stop 2–3 years
    # ago". Back-resolve each hit to OpenAlex by title (recovers real refs +
    # citations so it can join the trunk); only the genuinely-unindexed ones
    # stay as ref-less candidates, surfaced to the refiner via _frontier_candidates.
    ax_hits, seen_ax = [], set()
    for q in queries:
        for p in papers.ax_search(q, 8, from_year=max(NOW - 2, from_year or 0),
                                  to_year=to_year):
            ax = p.get("arxiv")
            if ax and ax not in seen_ax and on_topic(p, qsets, vocab):
                seen_ax.add(ax)
                ax_hits.append(p)
    n_ax_new = 0
    for p in ax_hits[:14]:                # cap the per-hit back-resolution calls
        oa = _resolve_arxiv_to_oa(p)
        if oa:
            add([oa], "ref")              # has an OpenAlex twin: joins the graph
        else:
            p["_no_refs"] = True
            add([p], "arxiv")             # truly new: frontier candidate only
            n_ax_new += 1
    if ax_hits:
        print(f"      arXiv: {len(ax_hits)} on-topic hits, {n_ax_new} new "
              f"preprint(s) not yet in OpenAlex", file=sys.stderr)

    if not seeds or not expand_hubs:
        return _topic_gate(pool, core, qsets, vocab), unresolved

    # pass 2 — snowball, but ONLY from core hubs: picking hubs by raw global
    # citations (or even by text match alone) expands from tangential
    # mega-cited papers and floods the pool with generic vision/ML classics.
    # Claude-proposed seeds (with refs) are always hubs — pulling their
    # references + citers gives the curated lineage its real ancestors/heirs.
    seed_hubs = [p for p in pool if p.get("_seed") and p.get("referenced_works")]
    hubs = sorted(core, key=lambda p: p.get("citations") or 0,
                  reverse=True)[:expand_hubs]
    for h in seed_hubs:
        if h not in hubs:
            hubs.append(h)

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
    return _topic_gate(pool, core, qsets, vocab), unresolved


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
    the core, or matches the topic loosely AND is genuinely embedded in the
    field's citation network. A loose keyword match plus a single citation tie
    is NOT enough — that lets *application* papers from another domain leak in
    (e.g. a diffusion-for-materials or metamaterials paper that cites DDPM but
    isn't part of image-generation). Such papers have **few core ties AND low
    overlap with the field's own vocabulary**, so we require either two core
    ties with some vocab overlap, or one tie with strong vocab overlap. Papers
    the API confirmed as all-terms ('precise') matches are trusted directly."""
    if len(core) < 3:
        return pool                       # core too thin to anchor the gate
    core_ids = {p["id"] for p in core}
    core_cite = Counter()                 # how many core papers cite p
    for p in core:
        for r in p.get("referenced_works") or []:
            core_cite[r] += 1

    def tie_count(p):
        return (core_cite.get(p["id"], 0)
                + len(set(p.get("referenced_works") or []) & core_ids))

    # generic giants (backbones, base datasets) loosely match the topic words
    # and ARE cited by the core — but their citation count dwarfs the field's
    cmax = max((p.get("citations") or 0) for p in core)
    cap = 30 * max(cmax, 100)
    kept, drift = [], 0
    for p in pool:
        if p.get("_seed"):
            kept.append(p)                 # Claude-curated: never gate it out
            continue
        if p["id"] in core_ids:
            kept.append(p)
            continue
        if (p.get("citations") or 0) > cap:
            continue                       # mega-cited generic dependency
        if p.get("_precise") and on_topic(p, qsets, vocab):
            kept.append(p)                 # API-confirmed every-term match
            continue
        if p.get("_via") == "arxiv" and on_topic(p, qsets, vocab):
            kept.append(p)                 # new preprint: frontier candidate only
            continue
        if not on_topic(p, qsets, vocab):
            continue
        tc, vo = tie_count(p), len(_node_terms(p) & vocab)
        if (tc >= 2 and vo >= 3) or (tc >= 1 and vo >= 6):
            kept.append(p)
        else:
            drift += 1                     # off-topic / domain-drift application
    dropped = len(pool) - len(kept)
    if dropped:
        print(f"      topic gate: dropped {dropped} off-topic candidates "
              f"({drift} as domain drift)", file=sys.stderr)
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

    def bucket(p):
        return sum(1 for c in cuts if p["year"] > c)

    # seeds first — Claude's curated picks are the whole point of this mode, so
    # the linked ones are reserved up front (era-capped so one era can't hog the
    # budget). Ref-less arXiv-only seeds aren't here — they have no links and
    # stay frontier candidates the refiner wires in by hand.
    # Take ALL linked seeds — a Claude-curated landmark beats any keyword-pool
    # paper (including domain-drift papers that merely cite the core), so seeds
    # fill the budget BEFORE founders/frontier/trunk. Only if seeds alone exceed
    # the budget do we trim to an era-balanced spread (rare; the user controls it
    # with --nodes). This is the whole point of seed mode: seeds win.
    seed_nodes = sorted((p for p in linked_pool if p.get("_seed")),
                        key=lambda p: p["_score"], reverse=True)
    if len(seed_nodes) <= k:
        for p in seed_nodes:
            take(p)
    else:
        percap = max(1, math.ceil(k / 4))
        for p in seed_nodes:                  # era-balanced first pass
            if len(chosen) >= k:
                break
            if sum(1 for c in chosen if bucket(c) == bucket(p)) < percap:
                take(p)
        for p in seed_nodes:                  # then fill leftover, ignore cap
            if len(chosen) >= k:
                break
            take(p)

    # founders — earliest era, must actually be cited by the field (top-up only)
    early = sorted((p for p in linked_pool
                    if p["year"] <= cuts[0] and p["_in_cited"] >= 1),
                   key=lambda p: (p["_in_cited"], p.get("citations") or 0),
                   reverse=True)
    for p in early[:2]:
        if len(chosen) >= k:
            break
        take(p)

    # frontier — last ~2 years, must build on the pool (or be a precise hit).
    # Method papers outrank surveys: a frontier slot should show where the
    # field is GOING, and one survey is plenty (top-up only — seeds may have
    # already filled it)
    nf, got = (3 if k >= 12 else 2), 0
    frontier = sorted((p for p in pool if p["year"] >= max(y1 - 1, NOW - 2)),
                      key=lambda p: (not _is_survey(p),
                                     (p.get("citations") or 0)
                                     + 5 * p["_in_cites"]), reverse=True)
    got = sum(1 for c in chosen if c["year"] >= max(y1 - 1, NOW - 2))
    for p in frontier:
        if got >= nf or len(chosen) >= k:
            break
        if _is_survey(p) and any(_is_survey(c) for c in chosen):
            continue
        if p["_in_cites"] >= 1 or (p.get("_precise") and p["_in_cited"] >= 1):
            got += take(p)

    # trunk — by in-field score, era-balanced; prefer connected candidates
    cap = max(2, math.ceil(k / 3))
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
def _augment_refs_via_s2(chosen):
    """Recent papers routinely have EMPTY OpenAlex reference lists (SD3, VAR, EDM
    all return 0), which leaves them orphaned in the citation graph. Fill the gaps
    from Semantic Scholar — the same fallback verify.py trusts: for a node whose
    OpenAlex refs don't reach the rest of the selection, pull its S2 references and,
    for any that match another selected node (normalized title / DOI / arXiv), add
    that node's OpenAlex id to this node's referenced_works so derive_edges links
    them. Real citations only — nothing invented. No-op if S2 is unavailable."""
    nt = {_norm_title(p["title"]): p["id"] for p in chosen if p.get("title")}
    doi = {str(p["doi"]).lower(): p["id"] for p in chosen if p.get("doi")}
    arx = {str(p["arxiv"]).lower(): p["id"] for p in chosen if p.get("arxiv")}
    ids = {p["id"] for p in chosen}
    filled = 0
    for p in chosen:
        have = set(p.get("referenced_works") or [])
        covered = len(have & ids)
        if len(have) >= 20 and covered >= 1:
            continue                          # OpenAlex data is good enough here
        titles, exts = papers.s2_reference_keys(p)
        if not titles and not exts:
            continue
        added = set()
        for t in titles:
            if t in nt and nt[t] != p["id"]:
                added.add(nt[t])
        for e in exts:
            if e in doi and doi[e] != p["id"]:
                added.add(doi[e])
            if e in arx and arx[e] != p["id"]:
                added.add(arx[e])
        new = added - have
        if new:
            p["referenced_works"] = sorted(have | new)
            filled += len(new)
    if filled:
        print(f"      S2 ref-fallback: added {filled} real citation link(s) "
              f"OpenAlex was missing", file=sys.stderr)


def _cites_via_s2(citing, cited):
    """Does `citing` reference `cited`, reconciled across duplicate records?
    Matches `cited` by normalized title / DOI / arXiv against `citing`'s
    Semantic Scholar reference keys (cached). Real citations only."""
    titles, exts = papers.s2_reference_keys(citing)
    if titles and _norm_title(cited.get("title")) in titles:
        return True
    e = set()
    if cited.get("doi"):
        e.add(str(cited["doi"]).lower())
    if cited.get("arxiv"):
        e.add(str(cited["arxiv"]).lower())
    return bool(e & exts)


def derive_edges(chosen, slug):
    """Citation-derived lineage: transitive reduction + nearest-predecessor
    parents + parallel-pair detection. Returns ready-to-render edge dicts."""
    _augment_refs_via_s2(chosen)
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
        # Final citation check before committing a `parallel`: `has_path` above
        # used OpenAlex refs only, which miss citations stored under a duplicate
        # work-id. Reconcile the ≤3 emitted pairs via S2 title/DOI keys (cached,
        # bounded) — a real citation means this is lineage, so emit a directed
        # `builds-on` instead. Same ground truth verify.py --fix uses.
        if _cites_via_s2(ids[b], ids[a]):          # later b cites earlier a
            edges.append({"from": slug[a], "to": slug[b],
                          "relation": "builds-on", "verified": "verified"})
        elif _cites_via_s2(ids[a], ids[b]):        # a cites b (unusual)
            edges.append({"from": slug[b], "to": slug[a],
                          "relation": "builds-on", "verified": "verified"})
        else:
            edges.append({"from": slug[a], "to": slug[b],
                          "relation": "parallel", "verified": "parallel"})
    _relabel(edges, ids, slug)
    return edges


def _cand_view(p):
    """Compact candidate entry for the draft's swap pools."""
    v = {"oa": p["id"], "title": p.get("title"),
         "authors": p.get("authors"), "year": p.get("year"),
         "venue": p.get("venue") or "", "citations": p.get("citations"),
         "in_pool_cites": p.get("_in_cites", 0),
         "cited_by_pool": p.get("_in_cited", 0),
         "abstract": (p.get("abstract") or "")[:240]}
    if p.get("_via") == "arxiv" or p.get("_no_refs"):
        v["source"] = ("arXiv preprint not yet in OpenAlex — verify by title "
                       "and wire its edges by hand before using as a node")
    return v


# -------------------------------------------------------------------- build --
def build(direction, chosen, pool=(), unresolved=()):
    taken, slug = set(), {}
    nodes = []
    # repair polluted / empty abstracts (e.g. an OpenAlex record whose abstract
    # is some unrelated repo's README — DDPM's "DiffuCpG …") from Semantic
    # Scholar, so the seeded problem/contribution summaries aren't garbage
    for p in chosen:
        if papers._abstract_looks_bad(p.get("title"), p.get("abstract")):
            fixed = papers.s2_abstract(p.get("title"), p.get("doi"),
                                       p.get("arxiv"))
            if fixed:
                p["abstract"] = fixed
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
    recent = [p for p in rest if p["year"] >= NOW - 2]
    # OpenAlex-grounded frontier (has refs/citations), score-ranked …
    oa_front = sorted((p for p in recent if p.get("_via") != "arxiv"
                       and (p.get("_in_cites", 0) >= 1 or p.get("_precise"))),
                      key=lambda p: ((p.get("citations") or 0)
                                     + 5 * p.get("_in_cites", 0)),
                      reverse=True)
    # … plus reserved slots for brand-new arXiv preprints (0 citations, so they
    # would always lose a score race — but they are exactly the freshest signal)
    ax_front = sorted((p for p in recent if p.get("_via") == "arxiv"),
                      key=lambda p: -(p.get("year") or 0))
    frontier_cands = (oa_front[:7] + ax_front[:4])[:11]
    alternates = [p for p in rest if p not in frontier_cands][:8]
    out = {"field": direction, "_stats": stats, "nodes": nodes,
           "edges": edges,
           "_frontier_candidates": [_cand_view(p) for p in frontier_cands],
           "_alternates": [_cand_view(p) for p in alternates]}
    if unresolved:
        # titles Claude proposed that resolved to NO real record — surfaced so
        # the refiner re-finds (better title / WebSearch / phrasing) or drops
        # them. They are never turned into nodes: no record, no node.
        out["_unresolved"] = list(unresolved)
    return out


def link_orphans(data, chosen, prune=False):
    """Auto-repair orphans: add a real builds-on edge when an orphan is cited by
    (or cites) a selected node. Crucially this matches by **normalized title**,
    not just OpenAlex id, so the common case where the citation is hidden behind
    a duplicate work-id (the same gap verify.py reconciles) gets linked
    automatically instead of landing on the human refiner. Orphans that remain
    unlinkable after this are dropped only when prune=True.

    Returns the number of edges added and nodes pruned."""
    orphans = list(data["_stats"]["orphans"])
    if not orphans:
        return 0, 0
    by_oa = {p["id"]: p for p in chosen}
    oa_of = {n["id"]: n["oa"] for n in data["nodes"]}
    title_of = {n["id"]: _norm_title(n.get("title")) for n in data["nodes"]}
    year_of = {n["id"]: (n.get("year") or 0) for n in data["nodes"]}

    # one batched fetch: normalized titles of every selected node's references
    ref_ids = sorted({r for p in chosen
                      for r in (p.get("referenced_works") or [])})
    id2title = {}
    for r in papers.oa_batch(ref_ids):
        if r.get("id") and r.get("title"):
            id2title[r["id"]] = _norm_title(r["title"])

    def ref_titles(slug):
        p = by_oa.get(oa_of.get(slug))
        return {id2title[r] for r in (p.get("referenced_works") or [])
                if r in id2title} if p else set()

    existing = {(e["from"], e["to"]) for e in data["edges"]}
    added = 0
    for o in orphans:
        cands = []                          # (parent_slug, child_slug)
        for c in title_of:
            if c == o:
                continue
            # c cites o  -> o is the (older) parent
            if title_of[o] and title_of[o] in ref_titles(c):
                cands.append((o, c))
            # o cites c  -> c is the parent
            if title_of[c] and title_of[c] in ref_titles(o):
                cands.append((c, o))
        # prefer links where the orphan is the CHILD (hang it off a real
        # ancestor); nearest predecessor first; cap at 2 new edges per orphan
        cands.sort(key=lambda fc: (fc[1] != o, -year_of[fc[0]]))
        for frm, to in cands[:2]:
            if (frm, to) in existing or (to, frm) in existing:
                continue
            data["edges"].append({"from": frm, "to": to,
                                  "relation": "builds-on", "verified": "verified"})
            existing.add((frm, to))
            added += 1

    # recompute health stats
    linked = {e["from"] for e in data["edges"]} | {e["to"] for e in data["edges"]}
    has_parent = {e["to"] for e in data["edges"] if e["relation"] != "parallel"}
    still = [n["id"] for n in data["nodes"] if n["id"] not in linked]
    pruned = 0
    if prune and still:
        keep = set(still) ^ {n["id"] for n in data["nodes"]}  # all but orphans
        data["nodes"] = [n for n in data["nodes"] if n["id"] in keep]
        data["edges"] = [e for e in data["edges"]
                         if e["from"] in keep and e["to"] in keep]
        pruned = len(still)
        linked = {e["from"] for e in data["edges"]} \
            | {e["to"] for e in data["edges"]}
        has_parent = {e["to"] for e in data["edges"]
                      if e["relation"] != "parallel"}
        still = [n["id"] for n in data["nodes"] if n["id"] not in linked]
    data["_stats"]["orphans"] = still
    data["_stats"]["roots"] = [n["id"] for n in data["nodes"]
                               if n["id"] not in has_parent and n["id"] in linked]
    return added, pruned


def suggest_aliases(direction, topn=8):
    """Step 0 aid: one seed search over the primary phrasing, then surface the
    field's most frequent title phrases as candidate alias sub-topics — so a
    user who only knows a nickname for the field can pick real index phrasings."""
    seeds = papers.oa_search(direction, 50, with_abstract=True)
    if not seeds:
        print("no seed papers — try a different (English) phrasing", file=sys.stderr)
        return
    bg, uni = Counter(), Counter()
    for p in seeds:
        ws = _surface_terms(p.get("title"))
        uni.update(ws)
        for i in range(len(ws) - 1):
            bg[f"{ws[i]} {ws[i + 1]}"] += 1
    print(f"# {len(seeds)} seed papers for “{direction}”")
    print("# candidate alias phrasings (frequent sub-topic phrases — keep the "
          "ones that name a real branch):")
    for ph, c in bg.most_common(topn * 2):
        if c >= 2 and ph not in direction.lower():
            print(f'    --alias "{ph}"   # appears in {c} titles')
    print("# frequent field terms (to compose your own phrasings):")
    print("    " + ", ".join(w for w, _ in uni.most_common(16)))


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
    ap.add_argument("--prune-orphans", action="store_true",
                    help="drop orphan nodes that stay unlinked after the "
                         "automatic title-aware repair (default: keep & flag)")
    ap.add_argument("--suggest-aliases", action="store_true",
                    dest="suggest_aliases",
                    help="Step 0 aid: print candidate alias phrasings mined from "
                         "a seed search, then exit (no draft is written)")
    ap.add_argument("--seed-titles", dest="seed_titles_file",
                    help="file of Claude-proposed paper titles (one per line, "
                         "# = comment); each is resolved to real metadata and "
                         "injected as a trusted node. The 'Claude proposes, "
                         "scripts verify' path — find titles with your knowledge "
                         "+ WebSearch, this grounds them.")
    ap.add_argument("--seed", action="append", default=[],
                    help="a single Claude-proposed title (repeatable; "
                         "alternative to --seed-titles)")
    ap.add_argument("--render", action="store_true")
    args = ap.parse_args()

    if args.suggest_aliases:
        suggest_aliases(args.direction)
        return

    seed_titles = list(args.seed)
    if args.seed_titles_file:
        with open(args.seed_titles_file, encoding="utf-8") as f:
            seed_titles += [ln.strip() for ln in f if ln.strip()
                            and not ln.lstrip().startswith("#")]

    label = " / ".join([args.direction] + args.alias) if args.alias \
        else args.direction
    print(f"[1/4] searching “{label}” …", file=sys.stderr)
    if seed_titles:
        print(f"      grounding {len(seed_titles)} Claude-proposed seed title(s)"
              " …", file=sys.stderr)
    pool, unresolved = collect(args.direction, args.alias, args.from_year,
                               args.to_year,
                               expand_hubs=0 if args.no_expand else 6,
                               seed_titles=seed_titles)
    if not pool:
        raise SystemExit("no papers found — try a different (English) phrasing")
    print(f"      {len(pool)} candidates "
          f"({sum(1 for p in pool if p.get('_via') != 'kw')} via snowball)",
          file=sys.stderr)

    print("[2/4] scoring in-field influence …", file=sys.stderr)
    score_pool(pool)

    print(f"[3/4] selecting {args.nodes} load-bearing nodes …", file=sys.stderr)
    chosen = select(pool, args.nodes)
    cyrs = [p["year"] for p in chosen if p.get("year")]
    if cyrs:
        recent = sum(1 for y in cyrs if y >= NOW - 2)
        print(f"      span {min(cyrs)}–{max(cyrs)}, {recent} node(s) in the "
              f"last 2y" + ("  ⚠ thin frontier — shop _frontier_candidates"
                            if recent < 3 else ""), file=sys.stderr)

    print("[4/4] deriving citation edges (transitive reduction) …",
          file=sys.stderr)
    data = build(args.direction, chosen, pool, unresolved)
    if data.get("_unresolved"):
        print(f"      ⚠ {len(data['_unresolved'])} seed title(s) did not "
              f"resolve — see _unresolved (re-find or drop, never invent)",
              file=sys.stderr)
    if data["_stats"]["orphans"]:
        added, pruned = link_orphans(data, chosen, prune=args.prune_orphans)
        if added or pruned:
            print(f"      orphan repair: linked {added} edge(s)"
                  + (f", pruned {pruned} node(s)" if pruned else ""),
                  file=sys.stderr)
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
