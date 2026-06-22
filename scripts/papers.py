#!/usr/bin/env python3
"""Fetch real paper metadata to reconstruct a research lineage (stdlib only).

Two backends:
  openalex  (default) — no API key, reliable. Set OPENALEX_MAILTO for the polite
            pool (faster). Recommended for keyless use.
  s2        — Semantic Scholar. Set S2_API_KEY to avoid the throttled shared pool.

Subcommands:
  search "<query>" [--limit N] [--source openalex|s2]
      Seed search for a research direction. Prints JSON sorted by citations.

  expand <paperId> [<paperId> ...] [--limit N] [--source ...]
      For each paper, fetch references (ancestors) and citations (descendants)
      so the genealogy can be built. Prints JSON.

paperId formats:
  openalex: an OpenAlex id (W2741809807), "doi:10.1145/..", or "arxiv:2106.01342"
  s2:       an S2 id, "arXiv:2106.01342", "DOI:..", "CorpusId:.."
"""
import argparse
import hashlib
import http.client
import json
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET


# ------------------------------------------------------------- disk cache -----
# OpenAlex/S2 records are effectively immutable for our purposes, and the
# pipeline re-resolves the same works repeatedly (draft → verify → re-run). A
# small on-disk cache (stdlib only) makes re-runs fast, reproducible, and gentle
# on the APIs' rate limits. Disable with RG_NO_CACHE=1; tune RG_CACHE_TTL (secs).
_CACHE_DIR = pathlib.Path(os.environ.get("RG_CACHE_DIR")
                          or (pathlib.Path.home() / ".cache"
                              / "research-genealogy"))
_CACHE_TTL = int(os.environ.get("RG_CACHE_TTL", str(14 * 24 * 3600)))
_CACHE_ON = os.environ.get("RG_NO_CACHE", "").lower() not in ("1", "true", "yes")


def _cache_get(url):
    if not _CACHE_ON:
        return None
    p = _CACHE_DIR / (hashlib.sha1(url.encode("utf-8")).hexdigest() + ".json")
    try:
        if p.is_file() and (time.time() - p.stat().st_mtime) < _CACHE_TTL:
            with open(p, encoding="utf-8") as f:
                return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    return None


def _cache_put(url, data):
    if not _CACHE_ON or data is None:
        return
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        tmp = _CACHE_DIR / (hashlib.sha1(url.encode("utf-8")).hexdigest()
                            + ".json")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except OSError:
        pass


def _http_json(url, headers=None, soft=False):
    """GET JSON with disk cache + exponential-backoff retry.

    soft=True is for optional *fallback* calls (e.g. Semantic Scholar's heavily
    throttled keyless pool): fewer retries and return None on failure instead of
    aborting, so a throttled fallback degrades to an honest 'unverified' rather
    than crashing the primary OpenAlex workflow."""
    cached = _cache_get(url)
    if cached is not None:
        return cached
    headers = dict(headers or {})
    headers.setdefault("User-Agent", "research-genealogy-skill")
    tries = 3 if soft else 6
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(
                urllib.request.Request(url, headers=headers), timeout=30
            ) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                _cache_put(url, data)
                return data
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code in (429, 500, 502, 503):
                if attempt == tries - 1:
                    break
                wait = 2 ** attempt
                print(f"[http {e.code}, retry in {wait}s]", file=sys.stderr)
                time.sleep(wait)
                continue
            if soft:
                return None
            raise
        except (urllib.error.URLError, ConnectionError, TimeoutError,
                http.client.HTTPException) as e:
            if attempt == tries - 1:
                break
            wait = 2 ** attempt
            print(f"[network error {e}, retry in {wait}s]", file=sys.stderr)
            time.sleep(wait)
    if soft:
        return None
    raise SystemExit("API failed after retries")


def _authors_label(names):
    names = [n for n in names if n]
    if not names:
        return ""
    return names[0] if len(names) == 1 else f"{names[0]} et al."


def _norm_title(t):
    """Title reduced to [a-z0-9] for robust cross-record matching (mirrors
    genealogy._norm_title)."""
    return re.sub(r"[^a-z0-9]", "", (t or "").lower())


def _title_close(a, b):
    na, nb = _norm_title(a), _norm_title(b)
    if not na or not nb:
        return False
    return na == nb or na in nb or nb in na


_BAD_ABS = re.compile(
    r"docker (?:pull|run)|git clone|pip install|conda install|"
    r"requirements\.txt|https?://github\.com|```", re.I)
# a real abstract is a single prose block; a full-text/body dump pasted in its
# place opens with section scaffolding ("1. Introduction", "1 Introduction In
# this study …") — the DDPM / W3036167779 case, whose stored abstract is an
# unrelated 'DiffuCpG' paper body
_BODY_DUMP = re.compile(r"\b\d{1,2}\.?\s+Introduction\b", re.I)


def _abstract_looks_bad(title, abstract):
    """Detect a polluted/garbage OpenAlex abstract — a repo README or a different
    paper's full text pasted in place of the real one. True when empty, code-like,
    or opening with section scaffolding instead of prose."""
    if not abstract or len(abstract) < 40:
        return True
    if _BODY_DUMP.search(abstract[:60]):
        return True
    return bool(_BAD_ABS.search(abstract))


# ---------------------------------------------------------------- OpenAlex ----
OA = "https://api.openalex.org"


def _oa_params(extra):
    p = dict(extra)
    mail = os.environ.get("OPENALEX_MAILTO")
    if mail:
        p["mailto"] = mail
    return p


def _abstract_from_inverted(inv):
    """OpenAlex returns abstracts as an inverted index {word: [positions]}."""
    if not inv:
        return None
    pos = {}
    for word, idxs in inv.items():
        for i in idxs:
            pos[i] = word
    return " ".join(pos[i] for i in sorted(pos)) or None


def _oa_slim(w, with_abstract=False):
    if not w:
        return None
    ids = w.get("ids") or {}
    arxiv = None
    loc = (w.get("primary_location") or {})
    src = (loc.get("source") or {})
    landing = loc.get("landing_page_url")
    doi = w.get("doi")
    if doi and doi.startswith("https://doi.org/"):
        doi = doi[len("https://doi.org/"):]
    names = [(a.get("author") or {}).get("display_name", "")
             for a in (w.get("authorships") or [])]
    out = {
        "id": (w.get("id") or "").replace("https://openalex.org/", ""),
        "title": w.get("title") or w.get("display_name"),
        "authors": _authors_label(names),
        "year": w.get("publication_year"),
        "venue": src.get("display_name") or "",
        "citations": w.get("cited_by_count"),
        "arxiv": arxiv,
        "doi": doi,
        "url": landing or ids.get("openalex"),
        "referenced_works": [r.replace("https://openalex.org/", "")
                             for r in (w.get("referenced_works") or [])],
    }
    if with_abstract:
        out["abstract"] = _abstract_from_inverted(
            w.get("abstract_inverted_index"))
    return out


OA_FIELDS = ("id,title,display_name,publication_year,authorships,"
             "cited_by_count,primary_location,doi,ids,referenced_works")
OA_FIELDS_ABS = OA_FIELDS + ",abstract_inverted_index"


OA_SORT = {
    "relevance": None,                 # default: topical match blended w/ citations
    "citations": "cited_by_count:desc",
    "recent": "publication_date:desc",  # newest first — for frontier coverage
}


def oa_search(query, limit, from_year=None, to_year=None, sort="relevance",
              precise=False, with_abstract=False):
    # default (relevance) ranking blends topical match with citations — far more
    # on-topic than a raw cited_by_count sort, which surfaces tangential giants.
    params = {"per_page": limit,
              "select": OA_FIELDS_ABS if with_abstract else OA_FIELDS}
    filters = []
    if precise:
        # title+abstract match: every term must appear -> kills off-topic giants,
        # essential when combining with a year window + citation sort (frontier).
        filters.append(f"title_and_abstract.search:{query}")
    else:
        params["search"] = query
    if from_year:
        filters.append(f"from_publication_date:{from_year}-01-01")
    if to_year:
        filters.append(f"to_publication_date:{to_year}-12-31")
    if filters:
        params["filter"] = ",".join(filters)
    if OA_SORT.get(sort):
        params["sort"] = OA_SORT[sort]
    data = _http_json(f"{OA}/works?" + urllib.parse.urlencode(_oa_params(params)))
    return [_oa_slim(w, with_abstract)
            for w in (data.get("results") if data else []) or []]


def oa_batch(ids, with_abstract=False):
    """Fetch metadata for many OpenAlex work ids in chunked requests."""
    out = []
    sel = OA_FIELDS_ABS if with_abstract else OA_FIELDS
    for i in range(0, len(ids), 40):
        chunk = [w for w in ids[i:i + 40] if w]
        if not chunk:
            continue
        data = _http_json(f"{OA}/works?" + urllib.parse.urlencode(_oa_params({
            "filter": "openalex_id:" + "|".join(chunk),
            "per_page": len(chunk), "select": sel})))
        out += [_oa_slim(w, with_abstract)
                for w in (data.get("results") if data else []) or []]
        time.sleep(0.15)
    return [p for p in out if p]


def oa_citers(pid, limit, with_abstract=False, sort="citations"):
    """Works that cite `pid`: most-cited (default), newest, or oldest first."""
    order = {"recent": "publication_date:desc",
             "oldest": "publication_date:asc"}.get(sort, "cited_by_count:desc")
    data = _http_json(f"{OA}/works?" + urllib.parse.urlencode(_oa_params({
        "filter": f"cites:{pid}", "per_page": limit, "sort": order,
        "select": OA_FIELDS_ABS if with_abstract else OA_FIELDS})))
    return [_oa_slim(w, with_abstract)
            for w in (data.get("results") if data else []) or []]


def _oa_norm_id(pid):
    if pid.lower().startswith(("doi:", "arxiv:")) or pid.startswith("W"):
        return pid
    return pid


def oa_expand(pid, limit, with_abstract=False):
    sel = OA_FIELDS_ABS if with_abstract else OA_FIELDS
    work = _http_json(f"{OA}/works/{urllib.parse.quote(_oa_norm_id(pid))}?"
                      + urllib.parse.urlencode(_oa_params({"select": sel})))
    if not work:
        return None
    me = _oa_slim(work, with_abstract)  # abstract on the focal paper only
    # ancestors: the works this paper references
    refs = []
    ref_ids = me.get("referenced_works", [])[:limit]
    if ref_ids:
        batch = "|".join(ref_ids)
        data = _http_json(f"{OA}/works?" + urllib.parse.urlencode(_oa_params({
            "filter": f"openalex_id:{batch}", "per_page": len(ref_ids),
            "select": OA_FIELDS,
        })))
        refs = [_oa_slim(w) for w in (data.get("results") if data else []) or []]
        refs.sort(key=lambda p: (p.get("citations") or 0), reverse=True)
    # descendants: works that cite this paper
    data = _http_json(f"{OA}/works?" + urllib.parse.urlencode(_oa_params({
        "filter": f"cites:{me['id']}", "per_page": limit,
        "sort": "cited_by_count:desc", "select": OA_FIELDS,
    })))
    cites = [_oa_slim(w) for w in (data.get("results") if data else []) or []]
    return {"paper": me, "references": refs, "citations": cites}


# ------------------------------------------------------------------- arXiv ----
# arXiv has the newest preprints (often months before OpenAlex indexes them),
# but NO citation graph. So its hits enrich frontier *recall* only: the caller
# back-resolves each to OpenAlex (by title) to recover real references, and the
# genuinely-new ones stay as ref-less candidates — never trunk nodes.
AX = "http://export.arxiv.org/api/query"
_ATOM = "{http://www.w3.org/2005/Atom}"


def _ax_entry(e):
    def txt(tag):
        el = e.find(_ATOM + tag)
        return re.sub(r"\s+", " ", (el.text or "").strip()) \
            if el is not None and el.text else ""

    aid = txt("id")                          # http://arxiv.org/abs/2403.12345v1
    m = re.search(r"abs/([0-9]+\.[0-9]+)", aid)
    arxiv = m.group(1) if m else None
    pub = txt("published")                   # 2024-03-15T17:00:00Z
    year = int(pub[:4]) if pub[:4].isdigit() else None
    names = [(a.find(_ATOM + "name").text or "").strip()
             for a in e.findall(_ATOM + "author")
             if a.find(_ATOM + "name") is not None]
    return {
        "id": f"arXiv:{arxiv}" if arxiv else (aid or None),
        "title": txt("title"), "authors": _authors_label(names), "year": year,
        "venue": "arXiv", "citations": None, "arxiv": arxiv, "doi": None,
        "url": aid or None,
        "referenced_works": [],              # arXiv exposes no reference list
        "abstract": txt("summary"),
    }


def ax_search(query, limit, from_year=None, to_year=None):
    """Search arXiv (newest first); return papers shaped like `_oa_slim` output
    but with no citations/references. Year-filters client-side (the API's date
    syntax is brittle). Degrades to [] on any failure — arXiv is a recall bonus,
    never load-bearing."""
    # AND the salient terms instead of a loose `all:<phrase>`: a date-sorted
    # `all:` match returns the newest paper containing ANY term (mostly noise),
    # while AND keeps it on-topic. Cap at 6 terms so it doesn't over-constrain.
    terms = [w for w in re.findall(r"[a-zA-Z][a-zA-Z0-9]{2,}", query)][:6]
    search = " AND ".join(f"all:{w}" for w in terms) or f"all:{query}"
    params = urllib.parse.urlencode({
        "search_query": search, "start": 0,
        "max_results": max(limit * 3, 20),   # over-fetch, then filter by year
        "sortBy": "submittedDate", "sortOrder": "descending"})
    url = f"{AX}?{params}"
    results = _cache_get(url)
    if results is None:
        raw = None
        for attempt in range(3):
            try:
                with urllib.request.urlopen(urllib.request.Request(
                    url, headers={"User-Agent": "research-genealogy-skill"}),
                        timeout=30) as resp:
                    raw = resp.read().decode("utf-8")
                break
            except (urllib.error.URLError, ConnectionError, TimeoutError,
                    http.client.HTTPException):
                if attempt == 2:
                    return []
                time.sleep(2 ** attempt)
        if not raw:
            return []
        try:
            root = ET.fromstring(raw)
        except ET.ParseError:
            return []
        results = [_ax_entry(e) for e in root.iter(_ATOM + "entry")]
        _cache_put(url, results)
    out = []
    for p in results:
        if not (p and p.get("id") and p.get("year") and p.get("title")):
            continue
        if (from_year and p["year"] < from_year) or \
                (to_year and p["year"] > to_year):
            continue
        out.append(dict(p))                  # copy: callers annotate freely
        if len(out) >= limit:
            break
    return out


# ----------------------------------------------------------- Semantic Scholar -
S2 = "https://api.semanticscholar.org/graph/v1"
S2_FIELDS = "title,year,authors,citationCount,venue,externalIds,url"


def _s2_headers():
    h = {}
    key = os.environ.get("S2_API_KEY")
    if key:
        h["x-api-key"] = key
    return h


def _s2_slim(p, with_abstract=False):
    if not p:
        return None
    ext = p.get("externalIds") or {}
    names = [a.get("name", "") for a in (p.get("authors") or [])]
    out = {
        "id": p.get("paperId"),
        "title": p.get("title"),
        "authors": _authors_label(names),
        "year": p.get("year"),
        "venue": p.get("venue") or "",
        "citations": p.get("citationCount"),
        "arxiv": ext.get("ArXiv"),
        "doi": ext.get("DOI"),
        "url": p.get("url"),
    }
    if with_abstract:
        out["abstract"] = p.get("abstract")
    return out


def s2_search(query, limit, from_year=None, to_year=None, sort="relevance",
              with_abstract=False, soft=False):
    fields = S2_FIELDS + (",abstract" if with_abstract else "")
    params = {"query": query, "limit": limit, "fields": fields}
    if from_year or to_year:
        params["year"] = f"{from_year or ''}-{to_year or ''}".strip("-") \
            if (from_year and to_year) else (f"{from_year}-" if from_year
                                             else f"-{to_year}")
    data = _http_json(
        f"{S2}/paper/search?" + urllib.parse.urlencode(params), _s2_headers(),
        soft=soft)
    papers = [_s2_slim(p, with_abstract)
              for p in (data.get("data") if data else []) or []]
    if sort == "recent":
        papers.sort(key=lambda p: (p.get("year") or 0), reverse=True)
    elif sort == "citations":
        papers.sort(key=lambda p: (p.get("citations") or 0), reverse=True)
    return papers


def s2_expand(pid, limit, with_abstract=False, soft=False):
    main = S2_FIELDS + (",abstract" if with_abstract else "")
    detail = _http_json(
        f"{S2}/paper/{urllib.parse.quote(pid, safe=':')}?" + urllib.parse.urlencode(
            {"fields": f"{main},references.{S2_FIELDS},citations.{S2_FIELDS}"}),
        _s2_headers(), soft=soft)
    if not detail:
        return None
    refs = [_s2_slim(r) for r in (detail.get("references") or []) if r]
    cites = [_s2_slim(c) for c in (detail.get("citations") or []) if c]
    refs = [r for r in refs if r and r.get("title")]
    cites = [c for c in cites if c and c.get("title")]
    refs.sort(key=lambda p: (p.get("citations") or 0), reverse=True)
    cites.sort(key=lambda p: (p.get("citations") or 0), reverse=True)
    return {"paper": _s2_slim(detail, with_abstract),
            "references": refs[:limit], "citations": cites[:limit]}


# ------------------------------------------- cross-source fallbacks (A2) -------
def s2_paper_id(node):
    """An S2-resolvable id for a lineage node / slim record (DOI > arXiv > url)."""
    if node.get("doi"):
        return "DOI:" + str(node["doi"]).replace("https://doi.org/", "")
    if node.get("arxiv"):
        return "arXiv:" + str(node["arxiv"])
    m = re.search(r"arxiv\.org/abs/([\d.]+)", node.get("url", "") or "")
    if m:
        return "arXiv:" + m.group(1)
    return None


def s2_abstract(title, doi=None, arxiv=None):
    """Fetch a clean abstract from Semantic Scholar when OpenAlex's is missing or
    polluted. Resolved by DOI/arXiv if available, else by a title-matched search."""
    pid = s2_paper_id({"doi": doi, "arxiv": arxiv})
    if pid:
        res = s2_expand(pid, 1, with_abstract=True, soft=True)
        if res and res.get("paper") and res["paper"].get("abstract") \
                and _title_close(res["paper"].get("title"), title):
            return res["paper"]["abstract"]
    if title:
        hits = s2_search(title, 3, with_abstract=True, soft=True)
        for h in hits or []:
            if h and h.get("abstract") and _title_close(h.get("title"), title):
                return h["abstract"]
    return None


def s2_reference_keys(node, limit=400):
    """(norm_titles, ext_ids) of a paper's references via Semantic Scholar — used
    to verify edges when OpenAlex's referenced_works list is empty (e.g. VQ-VAE,
    DALL·E 2). ext_ids are lowercased DOIs / arXiv ids."""
    pid = s2_paper_id(node)
    if not pid:
        hits = s2_search(node.get("title", ""), 1, soft=True)
        if hits and hits[0] and _title_close(hits[0].get("title"),
                                              node.get("title")):
            pid = hits[0]["id"]
    if not pid:
        return set(), set()
    res = s2_expand(pid, limit, soft=True)
    if not res:
        return set(), set()
    titles, exts = set(), set()
    for r in res.get("references", []):
        if r.get("title"):
            titles.add(_norm_title(r["title"]))
        for k in ("doi", "arxiv"):
            if r.get(k):
                exts.add(str(r[k]).lower())
    return titles, exts


# --------------------------------------------------- title resolution (v6) ----
def resolve_title(title, with_abstract=True):
    """Resolve a free-text paper title (proposed by Claude from knowledge or
    WebSearch) to a REAL metadata record — the grounding step that keeps the
    "Claude proposes, scripts verify" workflow zero-hallucination.

    Tries OpenAlex first (carries `referenced_works` → the paper can join the
    citation graph), then arXiv (often the only home of a brand-new preprint),
    then Semantic Scholar. Every candidate must pass `_title_close`, so a near
    miss is rejected rather than silently grabbing a different paper. Returns the
    record, or None if nothing matches — the caller must NOT invent one."""
    if not title or not title.strip():
        return None
    for h in oa_search(title, 5, with_abstract=with_abstract):
        if h and _title_close(h.get("title"), title):
            return h
    for h in ax_search(title, 5):
        if h and _title_close(h.get("title"), title):
            return h
    for h in (s2_search(title, 5, with_abstract=with_abstract, soft=True) or []):
        if h and _title_close(h.get("title"), title):
            return h
    return None


def resolve_titles(titles, with_abstract=True):
    """Resolve many titles; return (resolved_records, unresolved_titles)."""
    resolved, unresolved = [], []
    for t in titles:
        rec = resolve_title(t, with_abstract=with_abstract)
        if rec:
            resolved.append(rec)
        else:
            unresolved.append(t)
        time.sleep(0.1)
    return resolved, unresolved


# ----------------------------------------------------------------- dispatch ---
def cmd_search(args):
    if args.source == "openalex":
        papers = oa_search(args.query, args.limit, args.from_year,
                           args.to_year, args.sort, args.precise, args.abstract)
    elif args.source == "arxiv":
        papers = ax_search(args.query, args.limit, args.from_year, args.to_year)
    else:
        papers = s2_search(args.query, args.limit, args.from_year,
                           args.to_year, args.sort, args.abstract)
    papers = [p for p in papers if p and p.get("title")]
    for p in papers:
        p.pop("referenced_works", None)
    # keep the backend's relevance ranking; do NOT re-sort by raw citations
    # (that pushes off-topic mega-cited papers to the top).
    json.dump({"source": args.source, "query": args.query,
               "count": len(papers), "papers": papers},
              sys.stdout, ensure_ascii=False, indent=2)
    print()


def cmd_expand(args):
    fn = oa_expand if args.source == "openalex" else s2_expand
    out = []
    for pid in args.paper_ids:
        res = fn(pid, args.limit, args.abstract)
        if not res:
            print(f"[not found: {pid}]", file=sys.stderr)
            continue
        for key in ("paper",):
            if res.get(key):
                res[key].pop("referenced_works", None)
        for r in res.get("references", []) + res.get("citations", []):
            r.pop("referenced_works", None)
        out.append(res)
        time.sleep(0.2)
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
    print()


def cmd_resolve(args):
    titles = list(args.titles or [])
    if args.file:
        with open(args.file, encoding="utf-8") as f:
            titles += [ln.strip() for ln in f if ln.strip()
                       and not ln.lstrip().startswith("#")]
    resolved, unresolved = resolve_titles(titles, with_abstract=args.abstract)
    for p in resolved:
        p.pop("referenced_works", None)        # keep stdout compact
    json.dump({"count": len(titles), "resolved": resolved,
               "unresolved": unresolved},
              sys.stdout, ensure_ascii=False, indent=2)
    print()


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", choices=["openalex", "s2", "arxiv"],
                    default="openalex")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("search")
    s.add_argument("query")
    s.add_argument("--limit", type=int, default=30)
    s.add_argument("--from-year", type=int, dest="from_year",
                   help="only papers published in/after this year")
    s.add_argument("--to-year", type=int, dest="to_year",
                   help="only papers published in/before this year")
    s.add_argument("--sort", choices=["relevance", "citations", "recent"],
                   default="relevance",
                   help="recent = newest first (use for frontier coverage)")
    s.add_argument("--precise", action="store_true",
                   help="require all terms in title/abstract (OpenAlex only); "
                        "use for frontier/year-windowed searches to cut noise")
    s.add_argument("--abstract", action="store_true",
                   help="include the real abstract so summaries are grounded, "
                        "not recalled from memory")
    s.set_defaults(func=cmd_search)

    e = sub.add_parser("expand")
    e.add_argument("paper_ids", nargs="+")
    e.add_argument("--limit", type=int, default=40)
    e.add_argument("--abstract", action="store_true",
                   help="include the focal paper's real abstract")
    e.set_defaults(func=cmd_expand)

    r = sub.add_parser("resolve", help="ground Claude-proposed titles to real "
                       "metadata (OpenAlex/arXiv/S2); prints resolved + "
                       "unresolved so nothing is invented")
    r.add_argument("titles", nargs="*", help="paper titles (or use --file)")
    r.add_argument("--file", help="file with one title per line (# = comment)")
    r.add_argument("--abstract", action="store_true", default=True,
                   help="include abstracts (on by default for grounding)")
    r.set_defaults(func=cmd_resolve)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
