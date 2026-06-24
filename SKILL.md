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

- **Propose freely, but ground everything.** You SHOULD use your own knowledge
  and `WebSearch` to name the field's landmark and newest papers (that recall is
  the point — it beats a blind keyword search). But a proposed paper only becomes
  a node after it is **resolved to a real record** by the scripts (`papers.py
  resolve` / `--seed-titles`, OpenAlex / arXiv / Semantic Scholar). A title that
  resolves to nothing stays in `_unresolved` — **never invent its authors, year,
  venue, or citations to make it a node.** You *organize and narrate*; the
  scripts *certify*.
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

Not sure how a field is phrased in the literature? Mine candidates first:

```
python3 scripts/genealogy.py "<your best primary phrasing>" --suggest-aliases
```

It runs one seed search and prints the most frequent title phrases (real
sub-topic names) as ready-to-paste `--alias` lines — pick the ones that name a
genuine branch.

The final `field` label shown to the user stays in *their* language — edit it
in the JSON afterwards.

## Step 1 — research the field yourself (Claude proposes)

Before running the pipeline, **act like the expert being asked "调研一下 X 方向"**.
Using your own knowledge **and `WebSearch`**, name the papers that actually carry
the field's story — 15–25 candidate titles spanning:

- the **founding / landmark** works (the ones any survey opens with);
- the **high-impact middle** (the methods everyone builds on);
- the **2026 frontier** — and this is where `WebSearch` matters most, because
  OpenAlex lags on the newest work. Search the live web:
  `"<field> 2025 2026 survey"`, `"best <field> papers 2026 arXiv"`, the relevant
  benchmark/leaderboard or lab pages, recent arXiv listings.

Write the **exact titles** (resolution matches on the title) to `seeds.txt`, one
per line. Don't worry about getting metadata right — the next step grounds every
title to a real record and quarantines anything it can't find. You are supplying
*recall*; the scripts supply *proof*.

```
python3 scripts/papers.py resolve --file seeds.txt   # optional: preview what grounds
```

## Step 2 — generate the draft (one command)

```
python3 scripts/genealogy.py "<primary phrasing>" \
    --alias "<alias 1>" --alias "<alias 2>" --alias "<alias 3>" \
    --seed-titles seeds.txt \
    --nodes 14 --out lineage.json
```

`--seed-titles` resolves each title you proposed to real metadata and injects it
as a **trusted node** (and as a snowball hub, so its real ancestors/heirs join
the pool too). Titles that resolve nowhere land in the draft's `_unresolved`
list — **re-find or drop them in Step 3; never invent them.** Omit `--seed-titles`
to fall back to pure keyword search.

**Read the diagnostics it prints.** Each phrasing reports its `precise hits`,
and the pool reports its `core` size. If a phrasing got ~0 precise hits it
contributed nothing — replace it. If the core is thin (< 5) the relevance
gate is weak — re-phrase and re-run before investing in refinement. One
re-run with better phrasings beats an hour of manual repair.

What the command does (so you know what you can trust):

1. **seed grounding** (`--seed-titles`) — resolves the titles you proposed in
   Step 1 to real records and injects them as trusted nodes + snowball hubs;
   unresolved titles go to `_unresolved`, never invented;
2. multi-pass keyword search (broad + precise + frontier);
3. **arXiv frontier pass** — searches arXiv for the newest preprints (OpenAlex
   often lags months behind), back-resolves each to OpenAlex by title to recover
   real references; genuinely-unindexed ones are surfaced in
   `_frontier_candidates` (marked `source: arXiv …`) for you to verify and wire
   in by hand — they are never auto-added as trunk nodes;
4. **snowball expansion** — pulls references + citing works of the field's core
   papers (and your seeds), so landmarks the keywords missed still enter the pool;
5. relevance gating anchored on the *core* (the largest mutually-citing cluster
   of precise matches) — off-topic keyword twins and generic mega-cited
   backbones are dropped (your seeds are never gated out);
6. **in-field scoring** — nodes are ranked by citations *within the pool*, so
   the field's true landmarks beat globally-famous tangents;
7. era-stratified selection (your seeds reserved first, then founders + hubs +
   frontier), then edges straight from the real citation graph with **transitive
   reduction** (A→C is dropped when A→B→C exists) and **parallel detection**
   (same-era pairs that share references but don't cite each other).

Every `builds-on` edge in the draft is a real citation and arrives pre-marked
`"verified": "verified"`. The draft also carries:

- `_stats` — `orphans` (nodes with no edges) and `roots`;
- `_frontier_candidates` — strong recent (last ~2 years) papers that did NOT
  make the cut, with abstracts;
- `_alternates` — other high-scoring papers that just missed selection;
- `_unresolved` — seed titles that resolved to no real record (Step 3 handles).

Use the two candidate pools to **swap in better nodes without re-searching**.

## Step 3 — refine the draft (this is your real job)

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
2b. **Resolve the `_unresolved` list** (seed titles that grounded to nothing):
   for each, try a corrected/exact title (`papers.py resolve "<title>"`, or
   `WebSearch` for the real title), and if it now resolves, wire it in via
   `papers.py search "<title>" --abstract` + `expand`. If it still resolves to
   nothing, **drop it** — never promote an unresolved title to a node. Delete the
   `_unresolved` key when the list is handled.
3. **Rewrite every `problem` / `contribution`** as one crisp line each, in the
   user's language, from the node's `_abstract` — the seeded text is just the
   abstract's first sentence. `problem` = what was broken/missing before this
   paper; `contribution` = what it introduced. Delete the `_abstract` keys when
   done (keeps the file clean).
4. **Confirm / fix relation labels.** First let the *data* settle what it can —
   run `verify.py --fix` to auto-correct the edges real citations decide:
   ```
   python3 scripts/verify.py lineage.json --fix
   ```
   It swaps backwards `builds-on` arrows (↺ reversed) and converts any
   `parallel` edge that is really a citation (‼ cross-cite) into a directed
   `builds-on` — reconciled across duplicate OpenAlex records, so you don't
   hand-resolve these or apologize for them in the narrative. Honest `⚠`
   gaps and true `parallel` pairs are left untouched.

   Then handle what the data can't: edges are `builds-on` by default, but the
   draft also *guesses* some `inspired-by` / `supersedes` labels with a
   heuristic and flags each with `"_label_hint": "auto"` (rendered as a yellow
   `?`). **Confirm or correct each hinted edge from the abstracts** — they are
   guesses, not facts — and add the ones the heuristic missed:
   - `inspired-by` — conceptual influence rather than direct extension. Typical
     case: a *generation* milestone (e.g. DALL·E 2, Stable Diffusion) that
     triggered a detection/analysis wave — keep it as a root/context node but
     mark its outgoing edges `inspired-by`.
   - `supersedes` — the later method made the earlier one obsolete on the same
     problem.
   - `parallel` — independent same-era attacks on the same problem (the draft
     detects some; add ones you can argue from the abstracts).

   Delete the `_label_hint` key once you've confirmed (or fixed) an edge.
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

### Quality bar — enforced by lint.py

Run the gate before rendering — a non-zero exit means the genealogy is NOT done:

```
python3 scripts/lint.py lineage.json
```

It hard-checks exactly the rules below and fails on any unmet one:

- **Refinement finished**: no blank `problem`/`contribution`, no leftover
  `_abstract` keys, draft scaffolding (`_stats`, `_unresolved`, etc.) removed,
  summaries no longer raw abstract seeds.
- **No star topology**: the deepest chain is ≥ 3 edges and no node has 6+ direct
  children (reroute children to their real, *nearest* predecessor).
- **Reaches the present with a real frontier**: max year ≥ now−2 AND ≥ 3 nodes
  from the last ~2 years (a genealogy that stops 2–3 years ago is the #1 failure
  mode; a frontier that is all surveys warns).
- **Structure is visible**: ≥ 1 non-`builds-on` relation survives
  (`parallel`/`inspired-by`/`supersedes`) and the trunk branches; zero orphans.

Fix what it flags and re-run until it passes. (Curated/frozen example files use
`--curated` to relax the now-relative frontier check.)

## Step 4 — render

```
python3 scripts/render_tree.py lineage.json
```

Prints a colored view with a left year-axis, role markers
(● founder / ◉ hub / ★ frontier), relation-coded branches (`├──` builds-on,
`├┈┈` inspired-by), citation bars, dim `∥ parallel` cross-links, and per-edge
`✓`/`⚠` verification marks. `--no-color` for files/README, `--width N` to fix.

Other output formats via `--format`:
```
python3 scripts/render_tree.py lineage.json --format markdown   # report: tree + table + edges
python3 scripts/render_tree.py lineage.json --format figure-prompt  # image-model prompt
```

`figure-prompt` builds a ready-to-feed prompt for an image model (GPT-image /
Midjourney / DALL·E) that draws the genealogy as a publication figure. It has a
prose body (subject, swimlanes, color semantics, style + negative constraints)
**and a hard structure checklist** — every node and every edge listed verbatim,
with ✓/⚠ marks — so the model can only draw the real connections, never invent
them. The swimlanes come out as `路线①〈待命名〉`; **rename each to its real route
name** (the branch names from Step 3 #5) before feeding it. `--lang en` for an
English brief.

## Step 5 — deliver the report (the actual product)

Write the report to `<field-slug>-genealogy.md` AND present its narrative +
tree in the conversation. Everything in the user's language. Template:

```markdown
# <方向名> 发展历程

> 一句话定位这个方向 · <起始年>–<最新年> · N 篇关键论文 · 引用边均经 OpenAlex 验证

## 全景谱系树
<render_tree.py --no-color output, in a code block>

> 引用数取自 OpenAlex 单条记录，会因预印本/正式版被拆分而**低估**（经典论文
> 尤甚），仅作量级参考；谱系的价值在「谁建立在谁之上」的关系，不在这些数字。
> （只此一行说明，不要在正文里反复解释。）

## 发展历程

### 奠基（<years>）：<这一段在解决什么>
<谁最先把问题立起来，当时的背景，最初的方法是什么、为什么不够>

### <路线A名称>（<years>）
<这条路线为什么从主干分出来（前一代方法做不到什么）→ 代表工作依次
解决了什么 → 它后来被什么取代/吸收 → **明确点出它与相邻路线的 parallel/
supersedes 关系**（这条边就是故事，不能省）>

### <路线B名称>（<years>）
<同上；路线之间的 parallel/对比关系必须点明>

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
- **Each route states its relationship to the neighboring route(s)** in one
  sentence — `parallel`（同期之争）/ `supersedes`（取代）/ 分叉自哪个祖先.
  The edges are the genealogy's point; a route described in isolation wastes them.
- The 近两年前沿 section is mandatory and must name concrete new directions —
  a genealogy that stops 2–3 years ago is the #1 failure mode.

**Final gate before delivery** — run the report linter; it mechanically checks
that every node is actually discussed, the required sections exist, and the tree
block survived (a non-zero exit means the report is NOT done):

```
python3 scripts/lint.py lineage.json --report <field-slug>-genealogy.md
```

**Optional — a publication figure.** If the user wants a diagram, generate the
prompt with `render_tree.py lineage.json --format figure-prompt`, rename its
`〈待命名〉` swimlanes to your Step 3 branch names, and feed the *whole* output
(prose body **and** structure checklist) to an image model. See
[`examples/diffusion-models-figure-prompt.md`](examples/diffusion-models-figure-prompt.md).
To render the image automatically, pipe it through an OpenAI-compatible image
relay (中转站) running `gpt-image-2` with `scripts/gen_figure.py` — default relay
is ZenMux, `--relay wegoo` for the alternate (key/setup in
[`image-relay.md`](image-relay.md)):

```
python3 scripts/gen_figure.py lineage.json --out figure.png            # data → prompt → image (ZenMux)
python3 scripts/gen_figure.py <renamed-prompt>.md --out figure.png     # from a refined prompt
python3 scripts/gen_figure.py lineage.json --relay wegoo --out figure.png  # alternate relay
```

## Manual search passes (when the draft missed something)

```
python3 scripts/papers.py search "<direction>" --limit 30            # anchor
python3 scripts/papers.py search "<direction>" --precise --from-year 2024 \
    --sort citations --limit 15                                      # frontier
python3 scripts/papers.py --source arxiv search "<direction>" \
    --from-year 2025 --limit 15                                      # newest preprints
python3 scripts/papers.py search "<exact title>" --abstract --limit 1 # landmark
python3 scripts/papers.py resolve "<title A>" "<title B>" …          # ground a list
python3 scripts/papers.py expand <paperId> --limit 40                # lineage
```

`--precise` requires every term in title/abstract — use it whenever a relevance
search returns off-topic giants. `--from-year/--to-year` window, `--sort
relevance|citations|recent`. `--source arxiv` hits the newest preprints
directly; `resolve` grounds free-text titles you (or `WebSearch`) found.

## Robustness (so you fight the tool less)

- **Duplicate-record-aware verification.** OpenAlex often stores a paper under
  several work-ids, so "B cites A" can fail on an exact-id check even when the
  citation is real. `verify.py` now reconciles by normalized **title / DOI**
  before marking `⚠`, and **falls back to Semantic Scholar** when OpenAlex's
  reference list is empty — so genuine citations stop showing up as false `⚠`.
  A surviving `⚠` now much more likely means a real gap worth a look.
- **Polluted/empty abstracts** (e.g. an OpenAlex record whose abstract is some
  unrelated repo's README) are detected and **repaired from Semantic Scholar**,
  so your grounded summaries don't inherit garbage.
- **Orphan auto-repair.** `genealogy.py` now links orphan nodes to their real
  parents/children automatically (including the duplicate-record case) before
  writing the draft; `--prune-orphans` drops any that truly can't be linked.
  You should see far fewer orphans to fix by hand.
- **arXiv recall for the frontier.** Beyond OpenAlex/S2, a dedicated arXiv pass
  pulls the very newest preprints (which OpenAlex can lag months behind) so the
  "近两年前沿" section has fresh material. arXiv has no citation graph, so these
  hits enrich *recall* only: each is back-resolved to OpenAlex by title to
  recover real references, and any that are genuinely unindexed stay as
  ref-less `_frontier_candidates` you wire in by hand — the "edges are real
  citations" guarantee is never weakened.
- **Tighter topic gate.** Application/review papers from an adjacent domain
  (e.g. diffusion-for-materials when the field is image generation) that merely
  cite the core are now filtered as domain drift, so the pool stays on-topic.

## Notes

- Scripts use only the Python stdlib. Default backend is **OpenAlex** (no key);
  set `OPENALEX_MAILTO` for its faster polite pool. Semantic Scholar is used
  automatically as a **fallback** for missing reference lists / abstracts; set
  `S2_API_KEY` to avoid its throttled keyless pool.
- **Disk cache**: API responses are cached under `~/.cache/research-genealogy`
  (so draft → verify → re-run is fast and reproducible). `RG_NO_CACHE=1` to
  disable, `RG_CACHE_TTL=<seconds>` to tune, `RG_CACHE_DIR` to relocate.
- `genealogy.py --from-year/--to-year` scopes the whole genealogy (e.g. only
  the last decade); `--no-expand` skips the snowball for a quick draft;
  `--prune-orphans` drops unlinkable orphan nodes.
- **Regression guard**: `python3 scripts/selftest.py` checks the examples'
  invariants offline; `--online` also re-verifies them and runs a live draft.
- Quality over coverage: a tight, correct trunk beats an exhaustive mess.
