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
import http.client
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


def _http_json(url, headers=None):
    headers = dict(headers or {})
    headers.setdefault("User-Agent", "research-genealogy-skill")
    for attempt in range(6):
        try:
            with urllib.request.urlopen(
                urllib.request.Request(url, headers=headers), timeout=30
            ) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code in (429, 500, 502, 503):
                wait = 2 ** attempt
                print(f"[http {e.code}, retry in {wait}s]", file=sys.stderr)
                time.sleep(wait)
                continue
            raise
        except (urllib.error.URLError, ConnectionError, TimeoutError,
                http.client.HTTPException) as e:
            wait = 2 ** attempt
            print(f"[network error {e}, retry in {wait}s]", file=sys.stderr)
            time.sleep(wait)
    raise SystemExit("API failed after retries")


def _authors_label(names):
    names = [n for n in names if n]
    if not names:
        return ""
    return names[0] if len(names) == 1 else f"{names[0]} et al."


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
              with_abstract=False):
    fields = S2_FIELDS + (",abstract" if with_abstract else "")
    params = {"query": query, "limit": limit, "fields": fields}
    if from_year or to_year:
        params["year"] = f"{from_year or ''}-{to_year or ''}".strip("-") \
            if (from_year and to_year) else (f"{from_year}-" if from_year
                                             else f"-{to_year}")
    data = _http_json(
        f"{S2}/paper/search?" + urllib.parse.urlencode(params), _s2_headers())
    papers = [_s2_slim(p, with_abstract)
              for p in (data.get("data") if data else []) or []]
    if sort == "recent":
        papers.sort(key=lambda p: (p.get("year") or 0), reverse=True)
    elif sort == "citations":
        papers.sort(key=lambda p: (p.get("citations") or 0), reverse=True)
    return papers


def s2_expand(pid, limit, with_abstract=False):
    main = S2_FIELDS + (",abstract" if with_abstract else "")
    detail = _http_json(
        f"{S2}/paper/{urllib.parse.quote(pid, safe=':')}?" + urllib.parse.urlencode(
            {"fields": f"{main},references.{S2_FIELDS},citations.{S2_FIELDS}"}),
        _s2_headers())
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


# ----------------------------------------------------------------- dispatch ---
def cmd_search(args):
    if args.source == "openalex":
        papers = oa_search(args.query, args.limit, args.from_year,
                           args.to_year, args.sort, args.precise, args.abstract)
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


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", choices=["openalex", "s2"], default="openalex")
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

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
