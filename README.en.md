<div align="center">

# research-genealogy

**Input a research direction → get its development genealogy, not just a paper list.**

[中文](README.md) ｜ English

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
&nbsp;[![Claude Code Skill](https://img.shields.io/badge/Claude%20Code-Skill-8A63D2.svg)](https://claude.com/claude-code)

</div>

---

## What is this

`research-genealogy` is a [Claude Code](https://claude.com/claude-code) **skill**. You give it a research
direction (e.g. *"generated image detection"*, *"contrastive learning"*, *"diffusion models"*), it searches
the real literature, and it shows you **how the field actually evolved**:

> who founded it → the problem it tackled → who built on it → which lines ran in **parallel** → what got
> superseded → today's frontier.

The output is a **terminal ASCII genealogy tree** plus an **era-by-era narrative**. The key difference from a
"paper list" is that it draws the **relationships** between papers (branches, parallel lines, supersession) —
it is **non-linear**, not a flat timeline.

---

## See it first

Below is the genealogy for *diffusion-model image generation* (18 key papers, 2015 → 2025, citation edges
verified against OpenAlex / Semantic Scholar). Full report:
[`examples/diffusion-models-genealogy.md`](examples/diffusion-models-genealogy.md).

![Development of diffusion-model image generation: a horizontal, multi-lane timeline genealogy](assets/diffusion-genealogy.png)

This figure is exactly what the skill emits as a **terminal ASCII tree** (excerpt):

```
      ╭────────────────────────────────────────────────────────────────╮
      │ 扩散模型图像生成 (Diffusion Models)  ·  18 papers · 2015 → 2025 │
      ╰────────────────────────────────────────────────────────────────╯
 2015 │ ● Sohl-Dickstein ─ diffusion foundation (non-equilibrium thermodynamics)
 2019 │ ● Yang Song ─ NCSN (score matching) → Score-SDE (2020) → EDM (2022)   score/SDE backbone
 2020 │   └─ ◉ Ho — DDPM ✓   the spark: diffusion catches up to GANs
 2020 │        ├─ ○ J. Song — DDIM ✓  deterministic fast sampling
 2021 │        └─ ◉ Dhariwal — Beat GANs ✓   architecture + classifier guidance set SOTA
 2022 │             ├─ ★ Ho — CFG ✓  the text-to-image master switch → Imagen ✓
 2022 │             ├─ ◉ Ramesh — DALL·E 2 ✓   unCLIP line
 2022 │             └─ ◉ Rombach — LDM / Stable Diffusion ✓  latent diffusion (most-cited in tree)
 2023 │                  ├─ ★ Peebles — DiT ✓  Transformer backbone + scaling
 2024 │                  │   ├─ ★ Esser — SD3 ✓   rectified flow → FLUX.1 Kontext (2025) ⚠
 2024 │                  │   └─ ★ VAR ✓   autoregressive "next-scale" ∥ SD3 → Janus-Pro (2025) ⚠
 2023 │                  └─ ★ Zhang — ControlNet ✓  plug-and-play controllable generation

      ● founder  ◉ hub  ★ frontier · ├─ builds-on  ├┈ inspired-by  ∥ parallel  ⇒ supersedes
      citations: ✓ 13 verified · ∥ 1 parallel · ‼ 2 mutual · ⚠ 6 (recent refs not yet indexed upstream)
```

**How to read the tree:** a left **year axis**; a role marker before each node (**●** founder / **◉** hub /
**★** frontier); branch styles encode the relation (`├──` builds-on, `├┈┈` inspired-by); the bar on the right
is citation count; `∥` marks parallel same-era lines and `⇒` supersession; and each edge ends in a `✓` / `⚠`
mark for **whether the citation was verified**.

> Two more ready-made examples: [generated image detection](examples/generated-image-detection.md),
> [AI4Reaction (AI for chemical reactions)](examples/ai4reaction-genealogy.md).

---

## The problem it solves

When you want to quickly understand an unfamiliar field, existing tools give you everything *except* the layer
you actually want:

| Existing tools | What they give | What's missing |
| --- | --- | --- |
| Survey generators (SurveyForge, AutoSurvey…) | a survey organized **by theme** | not *who built on whom* |
| ResearchRabbit | a citation **graph** to read yourself | no narrative |
| Paper search (Semantic Scholar…) | a **list** | no lineage |

`research-genealogy` fills in that missing middle layer — the **lineage**: a readable genealogy of ideas, with
explicit `builds-on` / `parallel` / `supersedes` edges between nodes.

---

## Two core guarantees

The biggest risk with a tool like this is confidently fabricating papers. Two hard rules shut that down:

**① Zero hallucination — every paper is real.**
Every node comes from **real metadata** fetched from [OpenAlex](https://openalex.org) (or Semantic Scholar).
Claude *organizes and narrates*; it never *recalls* papers from memory. Each node's one-line summary is written
from the paper's **real abstract**. A title that resolves to nothing is quarantined in `_unresolved` and
**never becomes a node**.

**② Verifiable citations — every edge is real.**
Every `builds-on` edge in the genealogy corresponds to a **real citation** in the data. `scripts/verify.py`
checks each one and marks it `✓ verified` or `⚠ unverified`, and prints those marks right on the tree — so you
can trust the arrows, not just the boxes.

```
 2019 │     └── ◉ Ning Yu et al. ✓   █████░░  426     ← edge verified as a real citation
 2026 │     └── ★ Koutlis et al. ⚠   ·······    0     ← citation not found; flagged honestly
      …
      citations: ✓ 16 verified  ⚠ 0 to review   (run verify.py)
```

> All scripts use only the Python standard library — **no `pip install`, no API key required.**

---

## How it works

![Workflow: research direction → real citation-graph mining (OpenAlex) → lineage construction → non-linear genealogy report](assets/workflow.png)

Four stages, left to right, with a single "zero-hallucination" thread running through all of them:

| Stage | What it does |
| --- | --- |
| **① Direction → search phrasings** | Turn your direction (possibly a nickname or non-English term) into the 1 primary + 2–3 alias phrasings the literature actually uses. |
| **② Real citation-graph mining (OpenAlex)** | Multi-pass search (broad / precise / frontier) + a citation "snowball" over references and citing works, to pull in the field's core papers. |
| **③ Lineage construction** | Relevance gating → in-field scoring → edges derived from the real citation graph (with transitive reduction & parallel detection), producing a draft `lineage.json`. |
| **④ Non-linear genealogy report** | Claude refines each node's summary and relations from real abstracts, then renders the ASCII tree + an era-by-era report. |

**The key: Claude proposes, the scripts verify.** Stage ② is not blind keyword search — Claude first uses its
own knowledge **and live `WebSearch`** (the way you'd answer "research field X for me") to name the landmark and
newest papers, **but every proposed title must first resolve to a real record** before it can become a node.
That combines an expert's recall with hard grounding.

---

## Install

```bash
npx skills add unumbrela/research-genealogy -g -a claude-code
```

Or just drop this folder into `~/.claude/skills/research-genealogy/`.

---

## Use it

Once installed, just **ask in plain language** inside Claude Code:

> Map out the development of "generated image detection" for me
>
> Research the genealogy of the AI4Reaction direction

Claude turns the direction into English search phrasings (community nicknames like "AI4Reaction" included),
fetches real literature, builds and refines the genealogy, and hands you a **full report** — genealogy tree +
era-by-era narrative + a verified paper list — saved as a markdown file.

### Three ready-made examples

| Direction | One line | Report |
| --- | --- | --- |
| Diffusion-model image generation | 18 nodes, 5 lanes, 2015→2025, from DDPM to SD3 / autoregressive / unified multimodal | [diffusion-models-genealogy.md](examples/diffusion-models-genealogy.md) |
| Generated image detection | GAN forensics → frequency/generalization lines → diffusion shock in 3 parallel lines → CLIP frontier, 16/16 edges verified | [generated-image-detection.md](examples/generated-image-detection.md) |
| AI4Reaction (AI for chemical reactions) | 1995→2025, from expert systems to LLM chemistry agents, 17/19 edges verified | [ai4reaction-genealogy.md](examples/ai4reaction-genealogy.md) |

---

## Advanced usage

<details>
<summary><b>One-command draft from the CLI (no Claude conversation needed)</b></summary>

```bash
# Simplest: one direction → draft + render
python3 scripts/genealogy.py "generated image detection" --nodes 12 --render

# Niche / multi-branch directions: feed the field's other names as aliases
python3 scripts/genealogy.py "machine learning chemical reaction prediction" \
    --alias "retrosynthesis prediction deep learning" \
    --alias "reaction yield prediction machine learning" \
    --alias "large language models chemistry reactions" \
    --nodes 14 --render

# Best results: let Claude (knowledge + WebSearch) name the key + newest papers first,
# write them to seeds.txt, then ground them all to real records
python3 scripts/genealogy.py "diffusion models image generation" \
    --alias "latent diffusion text-to-image" \
    --seed-titles seeds.txt --nodes 14 --render
```

The draft pipeline is grounded in real metadata throughout: seed grounding (`--seed-titles`; titles that
resolve nowhere go to `_unresolved`, never invented) → multi-pass search (broad + precise + frontier) → arXiv
frontier pass → citation snowball → relevance gate → in-field scoring → edges from the real citation graph
(transitive reduction + nearest-predecessor + parallel detection). Every `builds-on` edge is a real citation by
construction and arrives pre-marked `✓ verified`.

A quality gate keeps half-finished genealogies from shipping:

```bash
python3 scripts/lint.py lineage.json     # fails on blank summaries, draft residue, star topology, a stale/thin frontier, orphans
```

Common flags: `--alias` (repeatable — synonyms merged into one pool), `--suggest-aliases` (mine candidate
phrasings first), `--from-year/--to-year` (scope the genealogy), `--no-expand` (skip the snowball for a quick draft).
</details>

<details>
<summary><b>Output formats (terminal tree / Markdown report / figure prompt)</b></summary>

```bash
python3 scripts/render_tree.py lineage.json                       # colored terminal tree (default)
python3 scripts/render_tree.py lineage.json --format markdown     # report: tree + paper table + edges
python3 scripts/render_tree.py lineage.json --format figure-prompt # prompt for an image model (+ hard structure checklist)
```

`--format figure-prompt` writes a ready-to-feed prompt for an image model (GPT-image / Midjourney / DALL·E): a
styled prose brief **plus a hard structure checklist** that lists every node and edge verbatim (with ✓/⚠ marks),
so the figure can only show the real, citation-grounded connections — never invented ones. `--lang en` for an
English brief. Example: [`examples/diffusion-models-figure-prompt.md`](examples/diffusion-models-figure-prompt.md).
</details>

<details>
<summary><b>Render the prompt to an actual PNG</b></summary>

Pipe the prompt through an OpenAI-compatible image relay running `gpt-image-2`:

```bash
python3 scripts/gen_figure.py lineage.json --out figure.png         # data → prompt → image (ZenMux by default)
python3 scripts/gen_figure.py lineage.json --relay wegoo --out figure.png  # alternate relay
```

Relay setup and API-key handling: [`image-relay.md`](image-relay.md).
</details>

<details>
<summary><b>Manual passes (full control)</b></summary>

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

Search flags: `--precise` (every term in title/abstract — cuts off-topic giants), `--from-year/--to-year`
(time window), `--sort relevance|citations|recent`, `--abstract` (ground summaries). Backends:
`--source openalex` (default, keyless) or `--source s2` (set `S2_API_KEY`). Set
`OPENALEX_MAILTO=you@example.com` for OpenAlex's faster pool.
</details>

<details>
<summary><b><code>lineage.json</code> schema</b></summary>

```json
{
  "field": "生成图像检测",
  "nodes": [
    {"id":"wang2020","title":"...","authors":"Wang et al.","year":2020,
     "venue":"CVPR","citations":1500,
     "problem":"<one-line problem>","contribution":"<one-line method>","url":"https://..."}
  ],
  "edges": [
    {"from":"marra2018","to":"wang2020","relation":"builds-on"}
  ]
}
```

`relation` ∈ `builds-on` | `inspired-by` | `parallel` | `supersedes`. A node may have several parents — that's
the point of a non-linear genealogy.
</details>

> The complete operational spec (the step-by-step flow Claude actually follows) lives in [`SKILL.md`](SKILL.md).

---

## License

[MIT](LICENSE)
