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
which approaches were superseded → today's frontier. Output is a terminal ASCII
tree (`--` connectors + text) plus a short narrative.

## Hard rules (avoid citation hallucination)

- **Never invent papers, authors, years, or venues from memory.** Every node in
  the genealogy MUST come from real metadata fetched by `scripts/papers.py`
  (OpenAlex / Semantic Scholar). Your job is to *organize and narrate*, not to
  *recall*.
- **Ground every summary.** Write each node's `problem` / `contribution` from the
  paper's real abstract (`--abstract`), not from memory.
- **Verify every edge.** After building the graph, run `scripts/verify.py` to
  confirm each `builds-on` edge is a real citation. Fix what it flags; leave
  honest ⚠ marks on edges OpenAlex can't confirm rather than overclaiming.
- If a paper you believe is important does not appear in the fetched data, run
  another targeted search for it rather than asserting it from memory.
- Keep the trunk small: pick the **承上启下 (load-bearing) nodes** — high
  citations AND/OR bridging role — not every paper. 8–20 nodes is a good tree.

## Fast path (recommended start)

One command builds a **draft** lineage.json — running all the search passes,
selecting nodes, and deriving `builds-on` edges straight from the real citation
graph (so most edges already verify ✓):

```
python3 scripts/genealogy.py "<direction>" --nodes 12 --out lineage.json
```

Then **refine the draft** (this is your real job): drop off-topic / duplicate
nodes, rewrite each `problem`/`contribution` into one crisp line from the node's
`_abstract`, relabel any `parallel`/`inspired-by` edges, and add a landmark the
draft missed. Finally `verify.py` → `render_tree.py`. Use the manual passes below
when you need finer control or the draft missed key papers.

## Workflow (manual / full control)

The search runs in **three deliberate passes** so the genealogy spans the whole
timeline — founders, the high-impact middle, AND recent frontier work. Do not
skip the frontier pass: a genealogy that stops 2–3 years ago is the #1 failure
mode.

1. **Anchor search — find the cluster & founders.**
   ```
   python3 scripts/papers.py search "<direction>" --limit 30
   ```
   Relevance ranking. Note the early high-citation papers (likely founders) and
   the recurring big names (likely hubs). If results look noisy (off-topic
   giants), re-run with `--precise` (requires every term in title/abstract).

2. **Landmark lookup — pin the canonical papers by title.** When you know a
   field-defining paper's title, search it directly to get its real id/metadata:
   ```
   python3 scripts/papers.py search "<exact paper title>" --limit 1
   ```
   This is the most reliable way to ground a node (avoids relevance noise).

3. **Frontier pass — REQUIRED, covers recent work.** Broad keyword + citation
   sort buries new papers (they have few citations yet), so use `--precise` with
   a year window:
   ```
   python3 scripts/papers.py search "<direction>" --precise --from-year 2024 \
       --sort citations --limit 15      # most-cited recent (emerging hits)
   python3 scripts/papers.py search "<direction>" --precise --from-year 2025 \
       --sort recent --limit 15         # newest first (bleeding edge)
   ```
   Pick 2–4 genuinely recent nodes (mark them with `frontier` role implicitly by
   their year — the renderer highlights the newest as ★).

4. **Expand the lineage.** For the load-bearing papers, pull references
   (ancestors) and citations (descendants) to *ground the edges* — confirm that
   a later paper really cites the earlier one before drawing `builds-on`:
   ```
   python3 scripts/papers.py expand <paperId> [<paperId> ...] --limit 40
   ```

5. **Build `lineage.json`.** From the *fetched* metadata, assemble a graph. Pull
   real abstracts so the one-line `problem`/`contribution` are grounded, not
   recalled:
   ```
   python3 scripts/papers.py search "<exact title>" --abstract --limit 1
   ```
   Schema (see `examples/lineage.example.json`):
   ```json
   {
     "field": "<direction>",
     "nodes": [
       {"id":"wang2020","title":"...","authors":"Wang et al.","year":2020,
        "venue":"CVPR","citations":1234,
        "problem":"<问题一句话>","contribution":"<贡献一句话>",
        "url":"https://..."}
     ],
     "edges": [
       {"from":"marra2018","to":"wang2020","relation":"builds-on"}
     ]
   }
   ```
   `relation` ∈ `builds-on` | `inspired-by` | `parallel` | `supersedes`.
   A node may have multiple parents — that is the point; capture branches and
   parallel lines, not just a chain.

6. **Verify the edges.** Confirm each citation edge is real, and write the
   status back so the renderer can show it:
   ```
   python3 scripts/verify.py lineage.json --write
   ```
   Statuses: `✓ verified` (B really cites A), `⚠ unverified` (no citation found —
   data gap or wrong link), `↺ reversed` (edge points the wrong way — flip it),
   `‼ cross-cite` (a `parallel` pair actually cites — consider `builds-on`).
   **Act on what it flags**: flip reversed edges, reconsider cross-cites, and for
   stubborn ⚠ either find the real link or leave it honestly marked.

7. **Render the genealogy.**
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

8. **Narrate.** Below the tree, write a short prose walk-through in the field's
   own language: "最早 X(year) 针对 <problem> 提出 <method>；Y(year) 在其基础上
   解决 <问题>；与之并行，Z 从 <角度> 切入……到今天 <最新工作>。" Cite each
   claim with the node it came from. End with open problems / current frontier.

## Notes

- Scripts use only the Python stdlib. Default backend is **OpenAlex** (no key);
  set `OPENALEX_MAILTO` for its faster polite pool. `--source s2` uses Semantic
  Scholar (set `S2_API_KEY` to avoid the throttled shared pool). Both back off
  and retry on HTTP 429.
- `--precise` (OpenAlex) requires every query term in the title/abstract — use
  it whenever a relevance search returns off-topic mega-cited papers, and always
  for the frontier pass.
- Quality over coverage: a tight, correct trunk beats an exhaustive mess.
