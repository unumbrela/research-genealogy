---
name: research-genealogy
description: >
  Given a research direction (e.g. "generated image detection", "对比学习",
  "neural machine translation"), research the literature and produce a
  NON-LINEAR development genealogy: a terminal ASCII tree (built from `--`
  connectors and text) plus a narrative tracing who proposed what, against
  which problem, what built on what, and which lines ran in parallel — from
  the founding work up to the latest. Use when the user wants to understand
  how a field evolved, not just a flat list or a theme-organized survey.
---

# Research Genealogy

Turn a research direction into a readable, **non-linear development genealogy**.

The value is NOT "another paper search". It is the *lineage*: founding work →
the problem it tackled → who built on it → which parallel branches emerged →
which approaches were superseded → today's frontier.

**The deliverable is a complete report** (saved as a markdown file AND shown in
the conversation): the genealogy tree plus a narrative that walks through the
whole development, era by era and branch by branch, with every claim tied to a
real paper. A bare tree or a bare list is NOT done.

## Hard rules (avoid citation hallucination)

- **Never invent papers, authors, years, or venues from memory.** Every node in
  the genealogy MUST come from real metadata fetched by the scripts (OpenAlex /
  Semantic Scholar). Your job is to *organize and narrate*, not to *recall*.
- **Ground every summary.** Write each node's `problem` / `contribution` from
  the paper's real abstract (the `_abstract` field in the draft, or
  `papers.py search "<title>" --abstract`), not from memory.
- **Edges must be real citations.** The draft's `builds-on` edges are derived
  from OpenAlex reference lists, so they are real by construction. If you add
  or redirect an edge by hand, confirm it with `scripts/verify.py` (or
  `papers.py expand`); leave honest ⚠ marks on edges you cannot confirm.
- If a paper you believe is important does not appear in the fetched data, run
  a targeted title search for it rather than asserting it from memory.
- Keep the trunk small: the **承上启下 (load-bearing) nodes**, not every paper.
  10–16 nodes is a good tree.

## Step 0 — turn the user's direction into search phrasings

The user's wording ("AI4Reaction", "生成图像检测", a lab's nickname for a
field) is usually NOT what the literature is indexed under. Before searching,
derive:

1. **one primary English phrasing** — the name the papers themselves use
   (e.g. AI4Reaction → "machine learning chemical reaction prediction");
2. **2–3 alias phrasings** covering the direction's main sub-tasks and
   synonyms (→ "retrosynthesis prediction deep learning", "reaction yield
   prediction machine learning", "large language models chemistry") —
   a field is always named several ways, and one query never covers all
   branches. Include one phrasing aimed at the *newest* wave (the LLM/
   foundation-model angle exists in almost every field since 2023).

The final `field` label shown to the user stays in *their* language — edit it
in the JSON afterwards.

## Step 1 — generate the draft (one command)

```
python3 scripts/genealogy.py "<primary phrasing>" \
    --alias "<alias 1>" --alias "<alias 2>" --alias "<alias 3>" \
    --nodes 14 --out lineage.json
```

**Read the diagnostics it prints.** Each phrasing reports its `precise hits`,
and the pool reports its `core` size. If a phrasing got ~0 precise hits it
contributed nothing — replace it. If the core is thin (< 5) the relevance
gate is weak — re-phrase and re-run before investing in refinement. One
re-run with better phrasings beats an hour of manual repair.

What the command does (so you know what you can trust):

1. multi-pass keyword search (broad + precise + frontier);
2. **snowball expansion** — pulls references + citing works of the field's core
   papers, so landmarks the keywords missed still enter the pool;
3. relevance gating anchored on the *core* (the largest mutually-citing cluster
   of precise matches) — off-topic keyword twins and generic mega-cited
   backbones are dropped;
4. **in-field scoring** — nodes are ranked by citations *within the pool*, so
   the field's true landmarks beat globally-famous tangents;
5. era-stratified selection (founders + hubs + frontier), then edges straight
   from the real citation graph with **transitive reduction** (A→C is dropped
   when A→B→C exists) and **parallel detection** (same-era pairs that share
   references but don't cite each other).

Every `builds-on` edge in the draft is a real citation and arrives pre-marked
`"verified": "verified"`. The draft also carries:

- `_stats` — `orphans` (nodes with no edges) and `roots`;
- `_frontier_candidates` — strong recent (last ~2 years) papers that did NOT
  make the cut, with abstracts;
- `_alternates` — other high-scoring papers that just missed selection.

Use the two candidate pools to **swap in better nodes without re-searching**.

## Step 2 — refine the draft (this is your real job)

Work through ALL of these, editing `lineage.json` directly:

1. **Prune & replace.** Drop nodes that are off-topic, redundant (two surveys
   covering the same ground), or pure infrastructure (a dataset paper that
   isn't a turning point). If a known landmark is missing, fetch it by title
   and wire it in:
   ```
   python3 scripts/papers.py search "<exact paper title>" --abstract --limit 1
   python3 scripts/papers.py expand <paperId> --limit 30   # ground its edges
   ```
2. **Fix orphans** (`_stats.orphans`): either find the node's real citation
   link via `expand` and add the edge, or delete the node. An orphan box helps
   nobody.
3. **Rewrite every `problem` / `contribution`** as one crisp line each, in the
   user's language, from the node's `_abstract` — the seeded text is just the
   abstract's first sentence. `problem` = what was broken/missing before this
   paper; `contribution` = what it introduced. Delete the `_abstract` keys when
   done (keeps the file clean).
4. **Relabel relations.** The draft marks everything `builds-on`. Use:
   - `inspired-by` — conceptual influence rather than direct extension. Typical
     case: a *generation* milestone (e.g. DALL·E 2, Stable Diffusion) that
     triggered a detection/analysis wave — keep it as a root/context node but
     mark its outgoing edges `inspired-by`.
   - `supersedes` — the later method made the earlier one obsolete on the same
     problem.
   - `parallel` — independent same-era attacks on the same problem (the draft
     detects some; add ones you can argue from the abstracts).
5. **Name the branches.** Identify the 2–4 lines of attack the tree contains
   (e.g. 频域路线 / CLIP特征路线 / 重建误差路线) — you'll use these names in
   the narrative, and the tree should visibly hang each branch off its own
   ancestor. If two branches are tangled, redirect primary edges so each
   branch's papers chain together.
6. **Secure the frontier.** The last ~2 years must contribute ≥ 3 nodes that
   represent *distinct new directions* (e.g. an LLM/foundation-model take, a
   new benchmark, a new paradigm) — not three lookalike surveys. Shop in
   `_frontier_candidates` and swap weak picks (0-citation book chapters,
   redundant reviews) for papers that show where the field is going.
7. (Only if you hand-edited edges) re-check them:
   ```
   python3 scripts/verify.py lineage.json --write
   ```

### Quality bar — check before rendering

- No star topology: the deepest chain should be ≥ 3 edges; a founder with
  6+ direct children means you should reroute children to their real,
  *nearest* predecessors.
- Every era is represented: founding work, the high-impact middle, AND ≥ 3
  nodes from the last ~2 years covering distinct new directions. A genealogy
  that stops 2–3 years ago is the #1 failure mode.
- ≥ 2 branches are visible and nameable; at least one `parallel` or
  `inspired-by` relation survives (a pure chain means you haven't found the
  field's structure).
- Zero orphans; every summary is grounded in its abstract.

## Step 3 — render

```
python3 scripts/render_tree.py lineage.json
```

Prints a colored view with a left year-axis, role markers
(● founder / ◉ hub / ★ frontier), relation-coded branches (`├──` builds-on,
`├┈┈` inspired-by), citation bars, dim `∥ parallel` cross-links, and per-edge
`✓`/`⚠` verification marks. `--no-color` for files/README, `--width N` to fix.

Other output formats via `--format`:
```
python3 scripts/render_tree.py lineage.json --format mermaid    # GitHub-renderable graph
python3 scripts/render_tree.py lineage.json --format markdown   # report: tree + table + edges
python3 scripts/render_tree.py lineage.json --format bibtex     # cite every node
python3 scripts/render_tree.py lineage.json --format drawio     # editable draw.io diagram
```

## Step 4 — deliver the report (the actual product)

Write the report to `<field-slug>-genealogy.md` AND present its narrative +
tree in the conversation. Everything in the user's language. Template:

```markdown
# <方向名> 发展历程

> 一句话定位这个方向 · <起始年>–<最新年> · N 篇关键论文 · 引用边均经 OpenAlex 验证

## 全景谱系树
<render_tree.py --no-color output, in a code block>

## 发展历程

### 奠基（<years>）：<这一段在解决什么>
<谁最先把问题立起来，当时的背景，最初的方法是什么、为什么不够>

### <路线A名称>（<years>）
<这条路线为什么从主干分出来（前一代方法做不到什么）→ 代表工作依次
解决了什么 → 它后来被什么取代/吸收>

### <路线B名称>（<years>）
<同上；路线之间的 parallel/对比关系要点明>

### 转折：<外部冲击是什么>（<year>）
<指向 inspired-by 节点：什么事件改写了问题本身，领域如何转向>

### 近两年前沿（<NOW-1>–<NOW>）
<≥3 个新方向，每个：它接着哪条路线、新在哪里、目前到什么程度>

### 开放问题
<3-5 条，从前沿论文的 limitation/未来工作中来，不要泛泛而谈>

## 论文清单
<render_tree.py --format markdown 的 Papers 表>
```

Hard rules for the narrative:

- **Every node appears in the narrative at least once**, cited as
  "作者 (年份)"; never introduce a paper that is not a node in the tree.
- Explain **causality, not chronology**: "B 在 A 的基础上解决了 X" beats
  "然后 B 出现了". The builds-on/inspired-by edges ARE the story.
- The 近两年前沿 section is mandatory and must name concrete new directions —
  a genealogy that stops 2–3 years ago is the #1 failure mode.

## Manual search passes (when the draft missed something)

```
python3 scripts/papers.py search "<direction>" --limit 30            # anchor
python3 scripts/papers.py search "<direction>" --precise --from-year 2024 \
    --sort citations --limit 15                                      # frontier
python3 scripts/papers.py search "<exact title>" --abstract --limit 1 # landmark
python3 scripts/papers.py expand <paperId> --limit 40                # lineage
```

`--precise` requires every term in title/abstract — use it whenever a relevance
search returns off-topic giants. `--from-year/--to-year` window, `--sort
relevance|citations|recent`.

## Notes

- Scripts use only the Python stdlib. Default backend is **OpenAlex** (no key);
  set `OPENALEX_MAILTO` for its faster polite pool. `--source s2` uses Semantic
  Scholar (set `S2_API_KEY`), but only OpenAlex provides the reference lists
  the genealogy is built from.
- `genealogy.py --from-year/--to-year` scopes the whole genealogy (e.g. only
  the last decade); `--no-expand` skips the snowball for a quick draft.
- Quality over coverage: a tight, correct trunk beats an exhaustive mess.
