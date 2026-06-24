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
    edge_hint = set()                    # edges whose relation is an auto guess
    for e in data.get("edges", []):
        f, t, rel = e["from"], e["to"], e.get("relation", "builds-on")
        if f not in nodes or t not in nodes:
            continue
        if e.get("verified"):
            edge_status[(f, t)] = e["verified"]
        if e.get("_label_hint"):
            edge_hint.add((f, t))
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
    return children, primary, primary_rel, annotations, edge_status, edge_hint


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
    children, primary, primary_rel, annotations, edge_status, edge_hint = \
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
              f"{C('∥',MAGENTA)} parallel"
              + (f"  ·  {C('?',YELLOW)} auto-labelled, confirm in refine"
                 if edge_hint else ""))
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
        if nid in primary and (primary[nid], nid) in edge_hint:
            vmark += " " + C("?", YELLOW)      # auto-labelled relation — confirm
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
            q = C(" ?", YELLOW) if (pid, nid) in edge_hint else ""
            line("", cont + "  " + C(f"{g} {arel}: {who}", MAGENTA, DIM) + q)

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
def render_markdown(data, nodes):
    global _USE_COLOR
    _USE_COLOR = False
    children, primary, primary_rel, annotations, edge_status, _ = \
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


# ---- image-generation figure prompt -----------------------------------------
# Auto-build a publication-figure prompt for an image model (GPT-image /
# Midjourney / DALL·E). The figure stays a *genealogy timeline*; the prompt just
# carries the rigor of a good scientific-figure brief — clear sections, a
# consistent color legend, a style spec, and (crucially) a HARD STRUCTURE
# CHECKLIST that lists every node and every edge verbatim so the model cannot
# invent connections. Claude only renames the structural lanes afterwards.
_LANG = "zh"

FIG_ROLE = {
    "zh": {"founder": "奠基", "hub": "枢纽", "frontier": "前沿", "other": "其他"},
    "en": {"founder": "founder", "hub": "hub", "frontier": "frontier",
           "other": "other"}}
FIG_ARROW = {
    "builds-on": {"zh": "细实线箭头 →", "en": "thin solid arrow →"},
    "inspired-by": {"zh": "虚线箭头 ⇢", "en": "dashed arrow ⇢"},
    "parallel": {"zh": "点线·无箭头 ∥", "en": "dotted line, no head ∥"},
    "supersedes": {"zh": "橙色粗箭头 ⇒", "en": "thick orange arrow ⇒"}}
CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"


def _lanes(children, primary, nodes):
    """Decompose the tree into structural swimlanes (one technical route each).

    A lane is a spine: a root (or branch-off node) followed by its earliest-child
    chain. Every *other* child opens a new lane tagged with the node it branches
    off. Children are already year-sorted in build_graph, so each lane reads
    left-to-right by year. Claude renames the lanes to real route names later.
    Returns an ordered list of (branch_from_id_or_None, [node_ids…])."""
    def yr(nid):
        return nodes[nid].get("year") or 9999
    roots = sorted([nid for nid in nodes if nid not in primary], key=yr)
    lanes, seen, pending = [], set(), [(r, None) for r in roots]

    def walk(start, branch_from):
        chain, cur = [], start
        while cur is not None and cur not in seen:
            seen.add(cur)
            chain.append(cur)
            kids = children.get(cur, [])          # already year-sorted
            for k in kids[1:]:                    # non-primary children → new lanes
                pending.append((k, cur))
            cur = kids[0] if kids else None
        if chain:
            lanes.append((branch_from, chain))

    while pending:
        start, bfrom = pending.pop(0)
        if start not in seen:
            walk(start, bfrom)
    return lanes


def _eras(nodes):
    """Group nodes into ≤4 time bands; the final band is the frontier
    (years ≥ max−2). Returns ordered [(label, y_lo, y_hi, [node_ids…])]."""
    years = sorted({n.get("year") for n in nodes.values() if n.get("year")})
    if not years:
        return []
    maxy = years[-1]
    front = [y for y in years if y >= maxy - 2]
    base = [y for y in years if y < maxy - 2]
    groups, nb = [], min(3, len(base))
    for i in range(nb):
        seg = base[i * len(base) // nb:(i + 1) * len(base) // nb]
        if seg:
            groups.append(seg)
    groups.append(front)
    names = {1: ["前沿"], 2: ["奠基", "前沿"], 3: ["奠基", "发展", "前沿"],
             4: ["奠基", "发展", "演进", "前沿"]}.get(
        len(groups), [f"阶段{i+1}" for i in range(len(groups))])
    by_year = {}
    for nid, n in nodes.items():
        if n.get("year"):
            by_year.setdefault(n["year"], []).append(nid)
    eras = []
    for name, seg in zip(names, groups):
        ids = [nid for y in seg for nid in by_year.get(y, [])]
        eras.append((name, seg[0], seg[-1], ids))
    return eras


def _short_title(t):
    """Abbreviate a paper title for a compact node label."""
    t = (t or "").split(":")[0].split(" — ")[0].split(" – ")[0].strip()
    return clip(t, 34)


def _cell(s):
    return str(s or "").replace("|", "\\|")


def _node_inline(nodes, role, nid):
    """'2020 Ho ◉' — year + author + role glyph, for lane / era listings."""
    n = nodes[nid]
    return f"{n.get('year') or '?'} {n.get('authors') or nid} {MARK[role[nid]][0]}"


def render_figure_prompt(data, nodes):
    global _USE_COLOR
    _USE_COLOR = False
    lang = _LANG if _LANG in ("zh", "en") else "zh"
    children, primary, primary_rel, annotations, edge_status, edge_hint = \
        build_graph(data, nodes)
    role, _ = roles(nodes, primary)
    lanes = _lanes(children, primary, nodes)
    eras = _eras(nodes)
    field = data.get("field", "(field)")
    ys = [n.get("year") for n in nodes.values() if n.get("year")]
    miny, maxy = (min(ys), max(ys)) if ys else ("?", "?")
    rname = FIG_ROLE[lang]
    edges = [e for e in data.get("edges", [])
             if e["from"] in nodes and e["to"] in nodes]

    def vmark(status):
        sym, _ = VERIFY_MARK.get(status or "", ("", ""))
        return sym or "—"

    era_en = {"奠基": "founding", "发展": "growth", "演进": "evolution",
              "前沿": "frontier"}
    def ename(nm):
        return era_en.get(nm, nm) if lang == "en" else nm
    era_phrase = " · ".join(
        f"{ename(nm)}({lo}–{hi})" for nm, lo, hi, _ in eras) or f"{miny}–{maxy}"

    L = []
    if lang == "zh":
        L += [f"# 《{field}》发展谱系 · 配图提示词", "",
              "> 用法：把下面 **「一、提示词正文」整体复制给图像模型**，并把 "
              "**「二、结构清单」一起贴上作为硬约束** —— 清单逐条列出了每个节点与"
              "每条连接，模型只能照此绘制，不得增删或臆造关系。重要：先按 "
              "**「三、给作者的话」** 把泳道改成真实路线名再投喂。", ""]
        L += ["## 一、提示词正文（整体投喂给图像模型）", ""]
        body = [
            f"请生成一张适合论文发表、学术海报或项目汇报使用的科研发展谱系图，"
            f"主题为“{field}”，用于清晰展示该方向从奠基工作到最新前沿的"
            f"**非线性发展脉络**：谁在谁的基础上推进、哪些路线并行、哪些被取代。",
            "",
            f"**整体布局**：从左到右为时间轴（{miny}–{maxy}），顶部标注年份刻度；"
            f"纵向划分为 {len(lanes)} 条平行**泳道**，每条泳道是一条技术路线，"
            f"路线内的论文按年份从左到右串联。主要时间分区：{era_phrase}。",
            "",
            "**泳道（技术路线，名称见下方清单，由作者命名）**："]
        for i, (bfrom, chain) in enumerate(lanes):
            tag = CIRCLED[i] if i < len(CIRCLED) else f"({i+1})"
            seq = " → ".join(_node_inline(nodes, role, c) for c in chain)
            bp = (f"（从 {nodes[bfrom].get('authors', bfrom)} 分出）"
                  if bfrom else "")
            body.append(f"- 路线{tag}〈待命名〉{bp}：{seq}")
        body += [
            "",
            "**节点表示**：每篇论文是一张简洁卡片，含作者+年份与简短标题；用角色标记"
            "区分重要性——● 奠基 / ◉ 枢纽（高影响）/ ★ 前沿（最新）。卡片的视觉强调"
            "随角色递增。",
            "",
            "**连接与数据流**：用箭头表达论文间关系，区分四种语义且全程一致——"
            "builds-on＝细实线箭头；inspired-by＝虚线箭头；parallel＝点线无箭头"
            "（同期并行）；supersedes＝橙色粗箭头（取代）。在 builds-on 边上标注 "
            "✓（已用引用核验）或 ⚠（参考文献待索引）作为诚实标记。"
            "**只允许绘制「结构清单」中列出的连接，不得新增或臆造。**",
            "",
            "**颜色语义（含义固定、不可混用）**：强调色（橙）用于 ★ 前沿节点、"
            "核心创新、supersedes 关系与最终输出；主色（蓝）用于 builds-on 主干与 "
            "◉ 枢纽节点；奠基色（绿）用于 ● 奠基节点；辅助灰用于 ○ 其他节点与 "
            "⚠ 未验证标记。",
            "",
            "**风格**：现代、简洁、专业的矢量化科研插图；白色或极浅灰背景；扁平化或"
            "轻微立体图标，线条清晰，模块边界明确，留白充足，对齐整齐，层级分明。"
            "仅保留必要简短标签（作者、年份、方法缩写、路线名），统一字体与字号，"
            "避免大段说明文字。",
            "",
            "**禁止**：复杂背景、过度渐变、强烈阴影、卡通化元素、装饰性粒子、与内容"
            "无关的图标、水印、Logo、乱码、错误公式或无法辨认的文字。"]
        L += ["> " + ln if ln else ">" for ln in body]
    else:
        L += [f"# “{field}” genealogy · figure prompt", "",
              "> Usage: copy **Section 1 (the prompt body) to the image model**, "
              "and paste **Section 2 (the structure checklist) with it as a hard "
              "constraint** — it lists every node and edge verbatim, so the model "
              "draws exactly these and invents nothing. First rename the lanes per "
              "**Section 3**.", ""]
        L += ["## 1 · Prompt body (give this to the image model)", ""]
        body = [
            f"Produce a publication-quality scientific figure (for a paper, poster "
            f"or talk) titled “{field}”, showing the **non-linear development "
            f"genealogy** of the field: who built on whom, which lines ran in "
            f"parallel, and what was superseded.",
            "",
            f"**Layout**: left-to-right time axis ({miny}–{maxy}) with a year scale "
            f"on top; {len(lanes)} parallel **swimlanes**, each a technical route, "
            f"its papers chained left-to-right by year. Time bands: {era_phrase}.",
            "",
            "**Lanes (technical routes; names in the checklist, set by the author)**:"]
        for i, (bfrom, chain) in enumerate(lanes):
            tag = CIRCLED[i] if i < len(CIRCLED) else f"({i+1})"
            seq = " → ".join(_node_inline(nodes, role, c) for c in chain)
            bp = (f" (branches off {nodes[bfrom].get('authors', bfrom)})"
                  if bfrom else "")
            body.append(f"- Lane {tag} ⟨rename⟩{bp}: {seq}")
        body += [
            "",
            "**Nodes**: each paper is a clean card with author+year and a short "
            "title; role markers rank importance — ● founder / ◉ hub (high-impact) "
            "/ ★ frontier (newest); visual emphasis scales with role.",
            "",
            "**Edges**: distinct, consistent arrow semantics — builds-on = thin "
            "solid arrow; inspired-by = dashed; parallel = dotted, no head "
            "(concurrent); supersedes = thick orange arrow. Mark builds-on edges "
            "✓ (citation-verified) or ⚠ (references not yet indexed). "
            "**Draw only the connections listed in the checklist; invent none.**",
            "",
            "**Color semantics (fixed, never mixed)**: accent orange = ★ frontier "
            "nodes, core innovations, supersedes edges and final outputs; primary "
            "blue = builds-on trunk and ◉ hubs; founder green = ● founders; muted "
            "grey = ○ other nodes and ⚠ unverified marks.",
            "",
            "**Style**: modern, clean, professional vector sci-illustration; white "
            "or very-light-grey background; flat icons, crisp lines, clear module "
            "borders, generous whitespace, tidy alignment. Keep only short labels "
            "(author, year, method abbr., lane name) in one consistent font.",
            "",
            "**Forbidden**: busy backgrounds, heavy gradients, strong shadows, "
            "cartoon elements, decorative particles, unrelated icons, watermarks, "
            "logos, garbled text, wrong formulas, or illegible text."]
        L += ["> " + ln if ln else ">" for ln in body]

    # ---- Section 2 — the hard structure checklist ----------------------------
    h2 = ("## 二、结构清单（硬约束 · 模型只能照此绘制）" if lang == "zh"
          else "## 2 · Structure checklist (hard constraint — draw exactly this)")
    canvas = (f"- 画布：16:9 横版，白色背景，顶部年份轴 {miny}–{maxy}；"
              f"{len(nodes)} 个节点，{len(edges)} 条连接，{len(lanes)} 条泳道。"
              if lang == "zh" else
              f"- Canvas: 16:9 landscape, white background, top year axis "
              f"{miny}–{maxy}; {len(nodes)} nodes, {len(edges)} edges, "
              f"{len(lanes)} lanes.")
    L += ["", h2, "", canvas, ""]

    # lane table
    L += [("### 泳道 → 节点" if lang == "zh" else "### Lanes → nodes"), "",
          ("| 泳道 | 分出自 | 节点（按年份） |" if lang == "zh"
           else "| Lane | Branches off | Nodes (by year) |"),
          "| --- | --- | --- |"]
    for i, (bfrom, chain) in enumerate(lanes):
        tag = CIRCLED[i] if i < len(CIRCLED) else f"({i+1})"
        bp = nodes[bfrom].get("authors", bfrom) if bfrom else "—"
        seq = " → ".join(_node_inline(nodes, role, c) for c in chain)
        L.append(f"| {tag} | {_cell(bp)} | {_cell(seq)} |")

    # node table
    L += ["", ("### 节点" if lang == "zh" else "### Nodes"), "",
          ("| 年份 | 作者 | 角色 | 引用 | 简短标题 | 核验 |" if lang == "zh"
           else "| Year | Author | Role | Cites | Short title | Verify |"),
          "| ---: | --- | --- | ---: | --- | :---: |"]
    for nid, n in sorted(nodes.items(), key=lambda kv: (kv[1].get("year") or 0)):
        st = edge_status.get((primary.get(nid), nid)) if nid in primary else None
        L.append(f"| {n.get('year') or ''} | {_cell(n.get('authors') or nid)} | "
                 f"{MARK[role[nid]][0]} {rname[role[nid]]} | "
                 f"{n.get('citations') if n.get('citations') is not None else ''} | "
                 f"{_cell(_short_title(n.get('title')))} | {vmark(st)} |")

    # edge table — EVERY edge, verbatim
    L += ["", ("### 连接（只画这些）" if lang == "zh"
               else "### Edges (draw only these)"), "",
          ("| 起点 | → | 终点 | 关系 | 箭头样式 | 核验 |" if lang == "zh"
           else "| From | → | To | Relation | Arrow style | Verify |"),
          "| --- | :---: | --- | --- | --- | :---: |"]
    for e in edges:
        f, t, rel = e["from"], e["to"], e.get("relation", "builds-on")
        arrow = FIG_ARROW.get(rel, {}).get(lang, rel)
        hint = " ?" if e.get("_label_hint") else ""
        L.append(f"| {_cell(nodes[f].get('authors', f))} {nodes[f].get('year','')}"
                 f" | → | {_cell(nodes[t].get('authors', t))} "
                 f"{nodes[t].get('year','')} | {rel}{hint} | {arrow} | "
                 f"{vmark(e.get('verified'))} |")

    # legend
    if lang == "zh":
        L += ["", "### 图例", "",
              "- 角色：● 奠基 / ◉ 枢纽 / ★ 前沿 / ○ 其他",
              "- 颜色：橙＝前沿·核心创新·supersedes·输出；蓝＝builds-on 主干·枢纽；"
              "绿＝奠基；灰＝其他·未验证",
              "- 核验：✓ 已用引用核验　⚠ 参考文献待索引　‼ 互引　∥ 并行　? 关系待确认"]
        L += ["", "## 三、给作者的话（投喂前先做）", "",
              f"1. 把上面 {len(lanes)} 条泳道〈待命名〉改成真实路线名"
              "（如 频域路线 / CLIP 特征路线 / 重建误差路线）。",
              "2. 核对带 `?` 的关系标签与所有 ⚠ 边——它们是自动猜测/未验证，"
              "确认或修正后再出图。",
              "3. 其余结构（节点、连接、颜色语义）已与 lineage.json 一致，请勿改动。"]
    else:
        L += ["", "### Legend", "",
              "- Roles: ● founder / ◉ hub / ★ frontier / ○ other",
              "- Colors: orange = frontier·core·supersedes·output; blue = "
              "builds-on trunk·hub; green = founder; grey = other·unverified",
              "- Verify: ✓ citation-verified  ⚠ refs not indexed  ‼ mutual  "
              "∥ parallel  ? relation to confirm"]
        L += ["", "## 3 · Before you feed it", "",
              f"1. Rename the {len(lanes)} ⟨rename⟩ lanes above to real route "
              "names (e.g. frequency route / CLIP-feature route / "
              "reconstruction-error route).",
              "2. Check every `?` relation label and ⚠ edge — they are auto "
              "guesses / unverified; confirm or fix before rendering.",
              "3. Everything else matches lineage.json — do not change it."]
    return "\n".join(L)


FORMATS = {"markdown": render_markdown,
           "figure-prompt": render_figure_prompt}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lineage")
    ap.add_argument("--format",
                    choices=["tree", "markdown", "figure-prompt"],
                    default="tree")
    ap.add_argument("--lang", choices=["zh", "en"], default="zh",
                    help="static text language for --format figure-prompt")
    ap.add_argument("--no-color", action="store_true")
    ap.add_argument("--width", type=int, default=0)
    args = ap.parse_args()

    global _USE_COLOR, _LANG
    _LANG = args.lang
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
