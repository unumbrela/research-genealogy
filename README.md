# research-genealogy

> Input a research direction → get its **development genealogy**, not just a paper list.

A [Claude Code](https://claude.com/claude-code) skill that researches the
literature for a field (e.g. *"generated image detection"*, *"对比学习"*,
*"neural machine translation"*) and lays out **how it evolved**: the founding
work → the problem it tackled → who built on it → which lines ran in **parallel**
→ what got superseded → today's frontier.

Output is a terminal **ASCII genealogy tree** (drawn with `--` connectors) plus a
short narrative — the relationships are **non-linear** (branches & parallel
lines), not a flat timeline.

*(real run; colored in a terminal — see `examples/generated-image-detection.md`)*

```
      ╭───────────────────────────────────────────────────────────╮
      │ 生成图像检测 (Generated / AI-Synthesized Image Detection) │
      │ 12 papers  ·  2018 → 2026                                 │
      ╰───────────────────────────────────────────────────────────╯
      │
 2018 │  ● Marra et al.   ██████░  389   ← 奠基：生成图像残留可检测指纹
      │     │
 2019 │     ├── ◉ Ning Yu et al.   ██████░  425   · GAN指纹归因
      │     │
 2019 │     ├┈┈ ○ Durall et al.   █████░░  176   ← 频域分支起点
      │     │   └── ○ Frank et al.   █████░░  209   ∥ parallel: Wang
      │     │       └── ○ Corvi et al.   ██████░  236   (扩散时代取证) ∥ DIRE/Ojha
      │     │
 2020 │     └── ◉ Sheng-Yu Wang et al.   ███████  994   ← CNNDetection 主干
      │           单一ResNet+强增广跨GAN泛化，最强基线
      │         │
 2023 │         ├── ◉ Utkarsh Ojha et al.   ██████░  269   · 冻结CLIP特征通用检测
      │         │   ├── ★ Cozzolino et al. ✦NEW   █████░░   85  (2024, CLIP SOTA)
      │         │   └┈┈ ★ Marco Willi et al. ✦NEW   ·······    0  (2026, 机制剖析)
      │         ├── ○ Zhendong Wang et al.   █████░░  222   · DIRE 重建误差判据
      │         │   └── ★ Ricker et al. ✦NEW   ████░░░   38  (2024, training-free)
      │         └── ★ Huan Liu et al. ✦NEW   ████░░░   64  (2024, FatFormer)
      │
      ● founder  ◉ hub  ★ frontier  ·  ├── builds-on  ├┈┈ inspired-by  ∥ parallel
```

> A left **year axis**, role markers (**●** founder / **◉** hub / **★** frontier),
> **relation-coded branches** (`├──` builds-on, `├┈┈` inspired-by), citation
> bars, and `∥ parallel` cross-links. The frontier pass guarantees recent
> (2024+) work is included, not just the classics.

## Why this is different

| Existing tools | What they give | What's missing |
| --- | --- | --- |
| Survey generators (SurveyForge, AutoSurvey…) | a survey organized **by theme** | not *who built on whom* |
| ResearchRabbit | a citation **graph** to read yourself | no narrative |
| Paper search (Semantic Scholar…) | a **list** | no lineage |

`research-genealogy` gives you the **lineage**: a readable genealogy of ideas
with explicit `builds-on` / `parallel` / `supersedes` edges.

## No hallucinated papers — and verifiable edges

Every node comes from **real metadata** fetched from [OpenAlex](https://openalex.org)
(or Semantic Scholar) — Claude *organizes and narrates*, it never *recalls* papers
from memory. Node summaries are written from the papers' **real abstracts**
(`--abstract`).

And the lineage itself is **checkable**: `scripts/verify.py` confirms that every
`builds-on` edge is a *real citation* in the data, marking each `✓ verified`,
`⚠ unverified`, `↺ reversed`, or `‼ cross-cite`. The genealogy shows the marks
inline — so you can trust the arrows, not just the boxes.

```
 2019 │     ├── ◉ Ning Yu et al. ✓   ██████░  425     ← edge verified as a real citation
 2020 │     │   └── ○ Frank et al. ⚠   █████░░  209    ← citation not found in OpenAlex; flagged honestly
      …
      citations: ✓ 8 verified  ⚠ 7 to review   (run verify.py)
```

Stdlib-only scripts, no pip install, no API key required.

## Install

```bash
npx skills add unumbrela/research-genealogy -g -a claude-code
```

Or drop this folder into `~/.claude/skills/research-genealogy/`.

## Use

In Claude Code, just ask:

> 帮我梳理「生成图像检测」这个方向的发展历程

Claude will refine a draft into a verified genealogy (see `SKILL.md`).

### One command (fast path)

```bash
python3 scripts/genealogy.py "generated image detection" --nodes 12 --render
```

Runs every search pass, selects load-bearing nodes spanning founders → frontier,
and **derives the `builds-on` edges from the real citation graph** — so the draft
is citation-grounded out of the box (most edges verify ✓ immediately). Claude then
refines summaries, prunes off-topic nodes, and relabels relations.

### Output formats

```bash
python3 scripts/render_tree.py lineage.json                     # colored terminal tree (default)
python3 scripts/render_tree.py lineage.json --format mermaid    # GitHub-renderable graph
python3 scripts/render_tree.py lineage.json --format markdown   # report: tree + table + edges
python3 scripts/render_tree.py lineage.json --format bibtex     # cite every node
python3 scripts/render_tree.py lineage.json --format drawio     # editable draw.io / diagrams.net diagram
```

### Manual passes (full control)

```bash
# anchor search (relevance); add --precise if results look off-topic
python3 scripts/papers.py search "generated image detection" --limit 25
# landmark lookup by exact title -> real id/metadata (+abstract to ground summary)
python3 scripts/papers.py search "CNN-Generated Images Are Surprisingly Easy to Spot" --abstract --limit 1
# frontier pass (REQUIRED): recent work that citation-sort would bury
python3 scripts/papers.py search "AI-generated image detection" --precise --from-year 2024 --sort citations --limit 15
# expand a hub to ground edges, verify, render
python3 scripts/papers.py expand W3034577585 --limit 25 --abstract
python3 scripts/verify.py lineage.json --write
python3 scripts/render_tree.py lineage.json
```

Search flags: `--precise` (every term in title/abstract — cuts off-topic
giants), `--from-year / --to-year` (time window), `--sort relevance|citations|recent`,
`--abstract` (ground summaries). Backends: `--source openalex` (default, keyless)
or `--source s2` (set `S2_API_KEY`). Set `OPENALEX_MAILTO=you@example.com` for
OpenAlex's faster pool.

## lineage.json schema

```json
{
  "field": "生成图像检测",
  "nodes": [
    {"id":"wang2020","title":"...","authors":"Wang et al.","year":2020,
     "venue":"CVPR","citations":1500,
     "problem":"<一句话问题>","contribution":"<一句话方法>","url":"https://..."}
  ],
  "edges": [
    {"from":"marra2018","to":"wang2020","relation":"builds-on"}
  ]
}
```

`relation` ∈ `builds-on` | `inspired-by` | `parallel` | `supersedes`.
A node may have several parents — that's the point.

## License

MIT
