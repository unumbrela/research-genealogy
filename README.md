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
      ╭────────────────────────────────────────────────────────╮
      │ 生成图像检测 (AI-Generated Image Detection)            │
      │ 12 papers  ·  2018 → 2026                              │
      ╰────────────────────────────────────────────────────────╯
      │
 2018 │  ● Francesco Marra et al.   █████░░  390     ← 奠基：GAN假图取证基准
      │     │
 2019 │     └── ◉ Ning Yu et al. ✓   █████░░  426    · 「GAN指纹」真伪判别+来源归因
      │         │
 2020 │         └── ○ Ricard Durall et al. ✓   █████░░  407   ← 频域路线：上采样频谱伪影
      │
 2019 │  ● Xu Zhang et al.   ██████░  498            · AutoGAN 模拟伪影，免目标GAN
      │     │
 2020 │     └── ◉ Sheng-Yu Wang et al. ✓   ██████░  996   ← CNNDetection 最强基线
      │           → builds-on: Francesco Marra   ∥ parallel: Ning Yu
      │
 2022 │  ● Aditya Ramesh et al.   ███████ 2280       ← 转折：DALL·E 2 引爆扩散时代
      │     │
 2023 │     ├┈┈ ○ Utkarsh Ojha et al. ✓   █████░░  272    · 冻结CLIP特征通用检测
      │     │
 2023 │     └┈┈ ○ Riccardo Corvi et al. ✓   █████░░  236  · GAN取证经验迁移到扩散
      │         │
 2023 │         └── ○ Zhendong Wang et al. ✓   █████░░  224  · DIRE 重建误差路线  ∥ Ojha
      │             │
 2024 │             └── ★ Davide Cozzolino et al. ✦NEW ✓   ████░░░  85  · CLIP检测刷新上限
      │                 │
 2025 │                 ├── ★ Yixuan Li et al. ✦NEW ✓   ██░░░░░  10   · FakeBench 可解释检测
 2026 │                 └── ★ Christos Koutlis et al. ✦NEW ✓  ·······  0  · 最新综述

      ● founder  ◉ hub  ★ frontier  ·  ├── builds-on  ├┈┈ inspired-by  ∥ parallel
      citations: ✓ 16 verified  ⚠ 0 to review
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
 2019 │     └── ◉ Ning Yu et al. ✓   █████░░  426     ← edge verified as a real citation
 2026 │     └── ★ Koutlis et al. ⚠   ·······    0     ← citation not found; flagged honestly
      …
      citations: ✓ 16 verified  ⚠ 0 to review   (run verify.py)
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
>
> 调研搜索 AI4Reaction 方向的发展历程

Claude turns the direction into English search phrasings (community nicknames
like "AI4Reaction" included), builds a citation-grounded draft, refines it,
and delivers a **full report** — genealogy tree + era-by-era narrative +
verified paper list — saved as markdown.

### Worked example: "调研搜索 AI4Reaction 方向的发展历程"

From that one ask, the skill derived 4 English phrasings (reaction prediction /
retrosynthesis / yield prediction / LLM chemistry), pulled 15 load-bearing
papers spanning **1995 → 2025** with 17/19 edges citation-verified, and wrote
the full report → [`examples/ai4reaction-genealogy.md`](examples/ai4reaction-genealogy.md).
A taste of the narrative:

> **转折一：闭环（2019）——从"纸面规划"到"动手做实验"**
> Coley (2019, Science) 把 AI 合成规划接上机器人流动化学平台，首次闭环
> "规划→执行"。这一步改写了问题本身：此前 AI4Reaction 是预测问题，此后它
> 逐渐变成自主化学问题——这正是四年后 LLM 代理浪潮的舞台。
>
> **转折二：LLM 冲击（2023–2024）** — Boiko (2023, Nature) 的 Coscientist
> 证明 GPT-4 可以自主完成"设计—执行—分析"的完整科研闭环；与之并行，
> Bran (2024) 的 ChemCrow 走"LLM+18 种化学工具"的代理框架路线……

…and the genealogy tree it hangs off (excerpt):

```
 1995 │  ● Hiroko Satoh et al.      SOPHIA：从反应数据库导出知识库（专家系统时代）
 2011 │     └── ○ Kayala et al.     首批 ML 反应预测
 2017 │         ├── ○ Coley et al.    「模板+ML」前向预测范式
 2019 │         │   ├── ◉ Schwaller    Molecular Transformer（纯文本路线）
 2024 │         │   │   ├── ★ Bran      ChemCrow：LLM+18 化学工具代理
 2025 │         │   │   │   └── ★ Song    多代理机器人 AI 化学家
 2019 │         │   └── ◉ Coley        AI 规划+机器人闭环合成 (Science)
 2023 │         │       └── ★ Boiko      Coscientist 自主科研 (Nature)
 2017 │         └── ○ Segler → Liu    神经符号 → seq2seq 逆合成路线
```

The same standard applies to the image-detection example:
[`examples/generated-image-detection.md`](examples/generated-image-detection.md)
(2018 GAN 取证 → 频域/泛化双路线 → 扩散冲击三路并行 → CLIP/可解释前沿,
16/16 edges verified).

### One command (fast path)

```bash
python3 scripts/genealogy.py "generated image detection" --nodes 12 --render

# niche / multi-branch directions: give the field's other names as aliases
python3 scripts/genealogy.py "machine learning chemical reaction prediction" \
    --alias "retrosynthesis prediction deep learning" \
    --alias "reaction yield prediction machine learning" \
    --alias "large language models chemistry reactions" \
    --nodes 14 --render
```

The draft pipeline (all from real OpenAlex metadata):

1. **multi-pass search** — broad + precise + frontier (recent work that
   citation-sort would bury);
2. **citation snowball** — references + citing works of the field's core
   papers, so landmarks the keywords missed still enter the pool;
3. **relevance gate** — anchored on the largest mutually-citing cluster of
   precise matches; off-topic keyword twins and generic mega-cited backbones
   (ResNet & friends) are dropped, and misdated duplicate records (a "2025"
   paper with thousands of citations) get their year fixed from the data;
4. **in-field ranking** — nodes scored by citations *within the pool*, so the
   field's true landmarks beat globally-famous tangents;
5. **lineage edges** — "B cites A" ⇒ `A --builds-on--> B`, then **transitive
   reduction** (drop A→C when A→B→C exists — a readable chain instead of a
   star), nearest-predecessor parents, and **parallel detection** (same-era
   pairs that share references but don't cite each other).

Every `builds-on` edge is a real citation by construction and arrives
pre-marked `✓ verified`. The draft also ships `_frontier_candidates` /
`_alternates` swap pools and per-phrasing diagnostics (`precise hits`, `core`
size) so the refiner knows when to re-phrase. Claude then refines summaries,
prunes/replaces nodes, relabels `inspired-by` / `supersedes` relations, and
delivers a full report — genealogy tree + era-by-era narrative — saved as
markdown (see `SKILL.md`; example: `examples/ai4reaction-genealogy.md`).

Flags: `--alias` (repeatable — synonyms / sub-branch phrasings merged into one
pool), `--from-year/--to-year` scope the genealogy, `--no-expand` skips the
snowball for a quick draft.

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
