#!/usr/bin/env python3
"""Render a research-genealogy lineage.json as a polished terminal view.

Design:
  • a left YEAR gutter gives a visible time axis
  • role-coded node markers:  ● founder   ◉ hub (highly cited)   ★ frontier (newest)   ○ other
  • relation-coded branches:  ├── builds-on    ├┈┈ inspired-by
    cross-branch links (parallel / supersedes) are shown as dim annotations
  • a citation strength bar, an ANSI-colored header card and a legend

Usage:
  python3 scripts/render_tree.py lineage.json [--no-color] [--width N]

Color auto-disables when output is not a TTY or NO_COLOR is set.
"""
import argparse
import json
import math
import os
import re
import shutil
import sys
import unicodedata


def dw(s):
    """Display width: CJK / wide chars count as 2 columns."""
    return sum(2 if unicodedata.east_asian_width(c) in ("W", "F") else 1
               for c in s)


def clip(s, width):
    """Truncate s to a display width, adding … if cut."""
    if dw(s) <= width:
        return s
    out, w = "", 0
    for c in s:
        cw = 2 if unicodedata.east_asian_width(c) in ("W", "F") else 1
        if w + cw > width - 1:
            return out + "…"
        out += c
        w += cw
    return out

LINEAGE_RELS = ("builds-on", "inspired-by")  # define tree parentage
BRANCH = {"builds-on": ("├──", "└──"), "inspired-by": ("├┈┈", "└┈┈")}
REL_GLYPH = {"parallel": "∥", "supersedes": "⇒",
             "builds-on": "→", "inspired-by": "⇢"}

# ---- color -------------------------------------------------------------------
_USE_COLOR = True


def C(s, *codes):
    if not _USE_COLOR or not codes:
        return s
    return "\033[" + ";".join(codes) + "m" + s + "\033[0m"


BOLD, DIM = "1", "2"
GREEN, CYAN, YELLOW, BLUE, MAGENTA, GREY = "32", "36", "33", "34", "35", "90"


# ---- model -------------------------------------------------------------------
def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise SystemExit(f"lineage file not found: {path}")
    except json.JSONDecodeError as e:
        raise SystemExit(f"invalid JSON in {path}: {e}")
    nodes = {n["id"]: n for n in data.get("nodes", [])}
    return data, nodes


VERIFY_MARK = {"verified": ("✓", "32"), "unverified": ("⚠", "33"),
               "reversed": ("↺", "31"), "cross-cite": ("‼", "31"),
               "parallel": ("", ""), "unresolved": ("?", "90")}


def build_graph(data, nodes):
    children = {nid: [] for nid in nodes}
    primary, primary_rel, annotations = {}, {}, {nid: [] for nid in nodes}
    incoming = {nid: [] for nid in nodes}
    extra = []
    edge_status = {}
    for e in data.get("edges", []):
        f, t, rel = e["from"], e["to"], e.get("relation", "builds-on")
        if f not in nodes or t not in nodes:
            continue
        if e.get("verified"):
            edge_status[(f, t)] = e["verified"]
        (incoming[t].append((f, rel)) if rel in LINEAGE_RELS
         else extra.append((f, t, rel)))

    def yr(nid):
        return nodes[nid].get("year") or 9999

    for nid, parents in incoming.items():
        if parents:
            # primary parent = the most recent predecessor (prefer builds-on on
            # ties) — hanging children off their nearest ancestor keeps the
            # lineage a chain of ideas instead of a star around the founder
            pid, rel = sorted(parents,
                              key=lambda pr: (yr(pr[0]) if yr(pr[0]) != 9999
                                              else -1, pr[1] == "builds-on"))[-1]
            primary[nid], primary_rel[nid] = pid, rel
            children[pid].append(nid)
    for nid, parents in incoming.items():
        for pid, rel in parents:
            if primary.get(nid) != pid:
                annotations[nid].append((pid, rel))
    for f, t, rel in extra:
        annotations[t].append((f, rel))
    for kids in children.values():
        kids.sort(key=lambda nid: (nodes[nid].get("year") or 9999))
    return children, primary, primary_rel, annotations, edge_status


def roles(nodes, primary):
    years = [n.get("year") for n in nodes.values() if n.get("year")]
    cites = sorted(n.get("citations") or 0 for n in nodes.values())
    max_year = max(years) if years else 0
    # hub threshold = 70th percentile of citation counts
    hub_cut = cites[int(len(cites) * 0.7)] if cites else 0
    role = {}
    for nid, n in nodes.items():
        y, c = n.get("year") or 0, n.get("citations") or 0
        if nid not in primary:
            role[nid] = "founder"
        elif max_year and y >= max_year - 2:   # last ~3 years = current front
            role[nid] = "frontier"
        elif c >= hub_cut and c > 0:
            role[nid] = "hub"
        else:
            role[nid] = "other"
    return role, max_year


MARK = {"founder": ("●", GREEN), "hub": ("◉", CYAN),
        "frontier": ("★", YELLOW), "other": ("○", GREY)}


def cite_bar(c, cmax, width=7):
    if not cmax or not c:
        return C("·" * width, GREY)
    # log scale so 38 vs 994 both read well
    frac = math.log(c + 1) / math.log(cmax + 1)
    fill = max(1, round(frac * width))
    return C("█" * fill, BLUE) + C("░" * (width - fill), GREY)


# ---- render ------------------------------------------------------------------
def render(data, nodes, term_w):
    children, primary, primary_rel, annotations, edge_status = \
        build_graph(data, nodes)
    role, max_year = roles(nodes, primary)
    has_verify = bool(edge_status)
    cmax = max((n.get("citations") or 0) for n in nodes.values()) or 0

    GUT = 5            # year gutter width
    RULE = C("│", GREY)
    out = []

    def line(gutter, body):
        out.append(f"{gutter:>{GUT}} {RULE} {body}")

    # header card
    yspan = [n.get("year") for n in nodes.values() if n.get("year")]
    span = f"{min(yspan)} → {max(yspan)}" if yspan else "?"
    title = data.get("field", "(field)")
    inner = max(dw(title) + 2, 56)
    inner = min(inner, term_w - GUT - 6)
    title = clip(title, inner - 2)
    bar = "─" * inner
    legend = (f"{C('●',GREEN)} founder  {C('◉',CYAN)} hub  "
              f"{C('★',YELLOW)} frontier  ·  ├── builds-on  ├┈┈ inspired-by  "
              f"{C('∥',MAGENTA)} parallel")
    meta = f"{len(nodes)} papers  ·  {span}"
    out.append(f"{'':>{GUT}} ╭{bar}╮")
    out.append(f"{'':>{GUT}} │ " + C(title, BOLD) + " " * (inner - 1 - dw(title)) + "│")
    out.append(f"{'':>{GUT}} │ " + C(meta, DIM) + " " * (inner - 1 - dw(meta)) + "│")
    out.append(f"{'':>{GUT}} ╰{bar}╯")
    out.append(f"{'':>{GUT}} {RULE}")

    visited = set()

    def emit(nid, prefix, is_last, rel):
        n = nodes[nid]
        glyph, color = MARK[role[nid]]
        if nid in primary:
            l, r = BRANCH.get(rel, BRANCH["builds-on"])
            conn = (r if is_last else l)
        else:
            conn = ""  # root
        marker = C(glyph, BOLD, color)
        author = C(n.get("authors") or nid, BOLD, color)
        tag = C(" ✦NEW", BOLD, YELLOW) if role[nid] == "frontier" else ""
        bar = cite_bar(n.get("citations") or 0, cmax)
        cites = C(f"{n.get('citations') or 0:>4}", DIM)
        vmark = ""
        if has_verify and nid in primary:
            st = edge_status.get((primary[nid], nid))
            sym, col = VERIFY_MARK.get(st, ("", ""))
            if sym:
                vmark = " " + (C(sym, col) if col else sym)
        head = f"{prefix}{conn} {marker} {author}{tag}{vmark}   {bar} {cites}"
        line(n.get("year") or "", head)

        cont = prefix + ("    " if is_last or nid not in primary else "│   ")
        avail = term_w - GUT - 6 - dw(cont)
        # title + one-line gist
        t = clip(n.get("title") or "", avail)
        line("", cont + C(f"“{t}”", DIM))
        prob, contrib = n.get("problem"), n.get("contribution")
        desc = f"{prob} ⇒ {contrib}" if prob and contrib else (contrib or prob)
        if desc:
            line("", cont + "  " + clip(desc, avail - 2))
        for pid, arel in annotations.get(nid, []):
            who = nodes.get(pid, {}).get("authors", pid)
            g = REL_GLYPH.get(arel, "·")
            line("", cont + "  " + C(f"{g} {arel}: {who}", MAGENTA, DIM))

        if nid in visited:
            if children.get(nid):
                line("", cont + C("… (see above)", GREY))
            return
        visited.add(nid)
        kids = children.get(nid, [])
        for i, k in enumerate(kids):
            line("", cont + C("│", GREY))
            emit(k, cont, i == len(kids) - 1, primary_rel.get(k, "builds-on"))

    rts = sorted([nid for nid in nodes if nid not in primary],
                 key=lambda nid: (nodes[nid].get("year") or 9999))
    for i, r in enumerate(rts):
        emit(r, "", True, "builds-on")
        if i < len(rts) - 1:
            line("", "")

    out.append("")
    out.append(f"{'':>{GUT}} " + C(legend, DIM))
    if has_verify:
        nver = sum(1 for s in edge_status.values() if s == "verified")
        nrev = sum(1 for s in edge_status.values()
                   if s in ("unverified", "reversed", "cross-cite"))
        out.append(f"{'':>{GUT}} " + C(
            f"citations: {C('✓','32')} {nver} verified  "
            f"{C('⚠','33')} {nrev} to review   (run verify.py)", DIM))
    return "\n".join(out)


# ---- alternate formats -------------------------------------------------------
def _mm_id(s):
    return re.sub(r"\W", "_", s)


def _mm_label(n):
    title = clip(n.get("title") or n["id"], 48).replace('"', "'")
    head = f"{n.get('authors') or n['id']} {n.get('year') or ''}".strip()
    c = n.get("citations")
    cite = f"<br/>{c} cites" if c is not None else ""
    return f"<b>{head}</b><br/>{title}{cite}"


MM_EDGE = {"builds-on": "-->", "inspired-by": "-.->",
           "parallel": "-.->", "supersedes": "==>"}


def render_mermaid(data, nodes):
    children, primary, primary_rel, annotations, _ = build_graph(data, nodes)
    role, _ = roles(nodes, primary)
    out = ["```mermaid", "graph TD",
           "  classDef founder fill:#dcfce7,stroke:#16a34a,color:#000;",
           "  classDef hub fill:#cffafe,stroke:#0891b2,color:#000;",
           "  classDef frontier fill:#fef9c3,stroke:#ca8a04,color:#000;",
           "  classDef other fill:#f1f5f9,stroke:#64748b,color:#000;"]
    for nid, n in nodes.items():
        out.append(f'  {_mm_id(nid)}["{_mm_label(n)}"]:::{role[nid]}')
    for e in data.get("edges", []):
        f, t, rel = e["from"], e["to"], e.get("relation", "builds-on")
        if f not in nodes or t not in nodes:
            continue
        arrow = MM_EDGE.get(rel, "-->")
        lbl = f"|{rel}|" if rel in ("parallel", "supersedes") else ""
        out.append(f"  {_mm_id(f)} {arrow}{lbl} {_mm_id(t)}")
    out.append("```")
    return "\n".join(out)


def render_markdown(data, nodes):
    global _USE_COLOR
    _USE_COLOR = False
    children, primary, primary_rel, annotations, edge_status = \
        build_graph(data, nodes)
    role, _ = roles(nodes, primary)
    ys = [n.get("year") for n in nodes.values() if n.get("year")]
    span = f"{min(ys)} → {max(ys)}" if ys else "?"
    L = [f"# {data.get('field', 'Research genealogy')}", "",
         f"> {len(nodes)} papers · {span} · generated by **research-genealogy**",
         "", "## Genealogy", "", render(data, nodes, 100), "",
         "## Papers", "",
         "| Year | Paper | Cites | Role | Citation |",
         "| ---: | --- | ---: | --- | :---: |"]
    vsym = {"verified": "✓", "unverified": "⚠", "reversed": "↺",
            "cross-cite": "‼", "parallel": "∥", "unresolved": "?"}
    for nid, n in sorted(nodes.items(),
                         key=lambda kv: (kv[1].get("year") or 0)):
        st = edge_status.get((primary.get(nid), nid), "")
        title = (n.get("title") or "").replace("|", "\\|")
        url = n.get("url") or ""
        paper = f"[{n.get('authors') or ''} — {title}]({url})" if url \
            else f"{n.get('authors') or ''} — {title}"
        L.append(f"| {n.get('year') or ''} | {paper} | "
                 f"{n.get('citations') if n.get('citations') is not None else ''}"
                 f" | {role[nid]} | {vsym.get(st, '—')} |")
    L += ["", "## Lineage edges", ""]
    for e in data.get("edges", []):
        f, t, rel = e["from"], e["to"], e.get("relation", "builds-on")
        if f in nodes and t in nodes:
            mark = vsym.get(e.get("verified", ""), "")
            L.append(f"- {nodes[f].get('authors','')} {nodes[f].get('year','')} "
                     f"**—{rel}→** {nodes[t].get('authors','')} "
                     f"{nodes[t].get('year','')} {mark}")
    return "\n".join(L)


def _bib_escape(s):
    return (s or "").replace("{", "").replace("}", "")


def render_bibtex(data, nodes):
    out = []
    for nid, n in sorted(nodes.items(),
                         key=lambda kv: (kv[1].get("year") or 0)):
        venue = n.get("venue") or ""
        etype = "inproceedings" if re.search(
            r"conf|proc|workshop|symp|CVPR|ICCV|ECCV|NeurIPS|ICML|ICLR|ACL|"
            r"EMNLP|AAAI|KDD", venue, re.I) else "article"
        field = "booktitle" if etype == "inproceedings" else "journal"
        lines = [f"@{etype}{{{nid},",
                 f"  title = {{{_bib_escape(n.get('title'))}}},",
                 f"  author = {{{_bib_escape(n.get('authors'))}}},"]
        if n.get("year"):
            lines.append(f"  year = {{{n['year']}}},")
        if venue:
            lines.append(f"  {field} = {{{_bib_escape(venue)}}},")
        if n.get("doi"):
            lines.append(f"  doi = {{{n['doi']}}},")
        if n.get("url"):
            lines.append(f"  url = {{{n['url']}}},")
        lines.append("}")
        out.append("\n".join(lines))
    return "\n\n".join(out)


# ---- draw.io / diagrams.net (mxGraph XML) ------------------------------------
DRAWIO_FILL = {"founder": ("#d5e8d4", "#82b366"), "hub": ("#dae8fc", "#6c8ebf"),
               "frontier": ("#ffe6cc", "#d79b00"), "other": ("#f5f5f5", "#999999")}
# only structural lineage edges are drawn; parallel / inspired-by are omitted to
# keep the diagram clean (they remain in the tree/markdown views).
DRAWIO_EDGE = {  # (strokeColor, dashed, width)
    "builds-on": ("#6c8ebf", 0, 2), "supersedes": ("#b85450", 0, 3)}


def _xml_esc(s):
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _short_title(t):
    """Abbreviate a paper title for a compact node label."""
    t = (t or "").split(":")[0].split(" — ")[0].split(" – ")[0].strip()
    return clip(t, 34)


def render_drawio(data, nodes):
    children, primary, primary_rel, annotations, edge_status = \
        build_graph(data, nodes)
    role, _ = roles(nodes, primary)

    # X: tidy tree layout (parents centred over children); Y: ranked by year
    rts = sorted([n for n in nodes if n not in primary],
                 key=lambda n: (nodes[n].get("year") or 9999))
    xpos, slot = {}, [0]

    def assign(nid, guard):
        if nid in guard:
            return
        guard.add(nid)
        kids = children.get(nid, [])
        if not kids:
            xpos[nid] = slot[0]
            slot[0] += 1
        else:
            for k in kids:
                assign(k, guard)
            xpos[nid] = sum(xpos[k] for k in kids) / len(kids)
    for r in rts:
        assign(r, set())
    for nid in nodes:               # any node missed (cycle guard) gets a slot
        if nid not in xpos:
            xpos[nid] = slot[0]
            slot[0] += 1

    years = sorted({n.get("year") for n in nodes.values() if n.get("year")})
    ylevel = {y: i for i, y in enumerate(years)}
    W, H, XS, YS = 200, 64, 250, 160

    cells = []
    npos = {}   # nid -> (x, y) of the box, for edge routing
    # left-margin year axis — makes the timeline explicit
    for y in years:
        yy = ylevel[y] * YS
        cells.append(
            f'        <mxCell id="year{y}" value="{y}" '
            f'style="text;html=1;align=right;verticalAlign=middle;fontSize=14;'
            f'fontStyle=1;fontColor=#888;" vertex="1" parent="1">\n'
            f'          <mxGeometry x="-180" y="{yy}" width="110" height="{H}" '
            f'as="geometry"/>\n        </mxCell>')
    for nid, n in nodes.items():
        fill, stroke = DRAWIO_FILL[role[nid]]
        st = edge_status.get((primary.get(nid), nid))
        sym, _ = VERIFY_MARK.get(st, ("", ""))
        cites = n.get("citations")
        cline = (f"{cites} cites" if cites is not None else "") + \
                (f"  ·  {sym}" if sym else "")
        html = (f"<b>{_xml_esc((n.get('authors') or nid))} "
                f"{_xml_esc(n.get('year') or '')}</b><br>"
                f"<font style='font-size:10px'>{_xml_esc(_short_title(n.get('title')))}</font>"
                f"<br><font style='font-size:9px;color:#555'>{_xml_esc(cline)}</font>")
        style = (f"rounded=1;whiteSpace=wrap;html=1;fillColor={fill};"
                 f"strokeColor={stroke};arcSize=12;verticalAlign=middle;"
                 f"fontSize=11;spacing=4;shadow=1;")
        x = round(xpos[nid] * XS)
        y = ylevel.get(n.get("year"), 0) * YS
        npos[nid] = (x, y)
        cells.append(
            f'        <mxCell id="{_xml_esc(nid)}" value="{_xml_esc(html)}" '
            f'style="{style}" vertex="1" parent="1">\n'
            f'          <mxGeometry x="{x}" y="{y}" width="{W}" height="{H}" '
            f'as="geometry"/>\n        </mxCell>')

    for i, e in enumerate(data.get("edges", [])):
        f, t, rel = e["from"], e["to"], e.get("relation", "builds-on")
        if f not in nodes or t not in nodes or rel not in DRAWIO_EDGE:
            continue  # draw only builds-on / supersedes — keeps the canvas clean
        col, dash, wdt = DRAWIO_EDGE[rel]
        # leave the parent's bottom, enter the child's top; orthogonal routing.
        style = (f"edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;"
                 f"exitX=0.5;exitY=1;exitDx=0;exitDy=0;"
                 f"entryX=0.5;entryY=0;entryDx=0;entryDy=0;jettySize=18;"
                 f"strokeColor={col};strokeWidth={wdt};dashed={dash};"
                 f"endArrow=block;endFill=1;")
        # for edges spanning >1 year-level, force the horizontal run into the
        # clear channel just below the parent so it can't cross intermediate
        # boxes; the vertical drop then lands in the child's own column.
        sx, sy = npos[f]
        tx, _ = npos[t]
        gap = ylevel.get(nodes[t].get("year"), 0) - ylevel.get(nodes[f].get("year"), 0)
        geo = '<mxGeometry relative="1" as="geometry"/>'
        if gap >= 2:
            wy = sy + H + 28
            geo = ('<mxGeometry relative="1" as="geometry">'
                   f'<Array as="points"><mxPoint x="{tx + W // 2}" y="{wy}"/>'
                   '</Array></mxGeometry>')
        cells.append(
            f'        <mxCell id="e{i}" style="{style}" '
            f'edge="1" parent="1" source="{_xml_esc(f)}" target="{_xml_esc(t)}">\n'
            f'          {geo}\n        </mxCell>')

    body = "\n".join(cells)
    field = _xml_esc(data.get("field", "genealogy"))
    return (
        '<mxfile host="research-genealogy">\n'
        f'  <diagram name="{field}" id="genealogy">\n'
        '    <mxGraphModel dx="1100" dy="800" grid="1" gridSize="10" '
        'guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" '
        'pageScale="1" pageWidth="1654" pageHeight="1169" math="0" shadow="0">\n'
        '      <root>\n'
        '        <mxCell id="0"/>\n'
        '        <mxCell id="1" parent="0"/>\n'
        f'{body}\n'
        '      </root>\n'
        '    </mxGraphModel>\n'
        '  </diagram>\n'
        '</mxfile>')


FORMATS = {"mermaid": render_mermaid, "markdown": render_markdown,
           "bibtex": render_bibtex, "drawio": render_drawio}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lineage")
    ap.add_argument("--format",
                    choices=["tree", "mermaid", "markdown", "bibtex", "drawio"],
                    default="tree")
    ap.add_argument("--no-color", action="store_true")
    ap.add_argument("--width", type=int, default=0)
    args = ap.parse_args()

    global _USE_COLOR
    _USE_COLOR = (args.format == "tree" and not args.no_color
                  and sys.stdout.isatty() and os.environ.get("NO_COLOR") is None)
    term_w = args.width or shutil.get_terminal_size((100, 24)).columns
    term_w = max(70, min(term_w, 120))

    data, nodes = load(args.lineage)
    if not nodes:
        raise SystemExit("lineage.json has no nodes")
    if args.format == "tree":
        print(render(data, nodes, term_w))
    else:
        print(FORMATS[args.format](data, nodes))


if __name__ == "__main__":
    main()
