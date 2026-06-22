# 《扩散模型图像生成 (Diffusion Models for Image Generation)》发展谱系 · 配图提示词

> 用法：把下面 **「一、提示词正文」整体复制给图像模型**，并把 **「二、结构清单」一起贴上作为硬约束** —— 清单逐条列出了每个节点与每条连接，模型只能照此绘制，不得增删或臆造关系。重要：先按 **「三、给作者的话」** 把泳道改成真实路线名再投喂。

## 一、提示词正文（整体投喂给图像模型）

> 请生成一张适合论文发表、学术海报或项目汇报使用的科研发展谱系图，主题为“扩散模型图像生成 (Diffusion Models for Image Generation)”，用于清晰展示该方向从奠基工作到最新前沿的**非线性发展脉络**：谁在谁的基础上推进、哪些路线并行、哪些被取代。
>
> **整体布局**：从左到右为时间轴（2015–2025），顶部标注年份刻度；纵向划分为 7 条平行**泳道**，每条泳道是一条技术路线，路线内的论文按年份从左到右串联。主要时间分区：奠基(2015–2015) · 发展(2019–2020) · 演进(2021–2022) · 前沿(2023–2025)。
>
> **泳道（技术路线，名称见下方清单，由作者命名）**：
> - 路线①「扩散主干（DDPM 一脉）」：2015 Jascha Sohl‐Dickstein et al. ● → 2020 Ho, Jonathan et al. ◉ → 2020 Jiaming Song et al. ○
> - 路线②「分数 / SDE 路线」：2019 Yang Song et al. ● → 2020 Yang Song et al. ○ → 2022 Tero Karras et al. ○
> - 路线③「引导与提质」（从 Ho, Jonathan et al. 分出）：2021 Alex Nichol et al. ○ → 2021 Prafulla Dhariwal et al. ◉ → 2022 Jonathan Ho et al. ○ → 2022 Chitwan Saharia et al. ◉
> - 路线④「unCLIP 文生图」（从 Prafulla Dhariwal et al. 分出）：2022 Aditya Ramesh et al. ◉
> - 路线⑤「潜空间·架构演进」（从 Prafulla Dhariwal et al. 分出）：2022 Robin Rombach et al. ◉ → 2023 William Peebles et al. ★ → 2024 Patrick Esser et al. ★ → 2025 Black Forest Labs et al. ★
> - 路线⑥「可控生成」（从 Robin Rombach et al. 分出）：2023 Lvmin Zhang et al. ★
> - 路线⑦「自回归·统一多模态」（从 William Peebles et al. 分出）：2024 Yi Jiang et al. ★ → 2025 Xiaokang Chen et al. ★
>
> **节点表示**：每篇论文是一张简洁卡片，含作者+年份与简短标题；用角色标记区分重要性——● 奠基 / ◉ 枢纽（高影响）/ ★ 前沿（最新）。卡片的视觉强调随角色递增。
>
> **连接与数据流**：用箭头表达论文间关系，区分四种语义且全程一致——builds-on＝细实线箭头；inspired-by＝虚线箭头；parallel＝点线无箭头（同期并行）；supersedes＝橙色粗箭头（取代）。在 builds-on 边上标注 ✓（已用引用核验）或 ⚠（参考文献待索引）作为诚实标记。**只允许绘制「结构清单」中列出的连接，不得新增或臆造。**
>
> **颜色语义（含义固定、不可混用）**：强调色（橙）用于 ★ 前沿节点、核心创新、supersedes 关系与最终输出；主色（蓝）用于 builds-on 主干与 ◉ 枢纽节点；奠基色（绿）用于 ● 奠基节点；辅助灰用于 ○ 其他节点与 ⚠ 未验证标记。
>
> **风格**：现代、简洁、专业的矢量化科研插图；白色或极浅灰背景；扁平化或轻微立体图标，线条清晰，模块边界明确，留白充足，对齐整齐，层级分明。仅保留必要简短标签（作者、年份、方法缩写、路线名），统一字体与字号，避免大段说明文字。
>
> **禁止**：复杂背景、过度渐变、强烈阴影、卡通化元素、装饰性粒子、与内容无关的图标、水印、Logo、乱码、错误公式或无法辨认的文字。

## 二、结构清单（硬约束 · 模型只能照此绘制）

- 画布：16:9 横版，白色背景，顶部年份轴 2015–2025；18 个节点，22 条连接，7 条泳道。

### 泳道 → 节点

| 泳道 | 分出自 | 节点（按年份） |
| --- | --- | --- |
| ① | — | 2015 Jascha Sohl‐Dickstein et al. ● → 2020 Ho, Jonathan et al. ◉ → 2020 Jiaming Song et al. ○ |
| ② | — | 2019 Yang Song et al. ● → 2020 Yang Song et al. ○ → 2022 Tero Karras et al. ○ |
| ③ | Ho, Jonathan et al. | 2021 Alex Nichol et al. ○ → 2021 Prafulla Dhariwal et al. ◉ → 2022 Jonathan Ho et al. ○ → 2022 Chitwan Saharia et al. ◉ |
| ④ | Prafulla Dhariwal et al. | 2022 Aditya Ramesh et al. ◉ |
| ⑤ | Prafulla Dhariwal et al. | 2022 Robin Rombach et al. ◉ → 2023 William Peebles et al. ★ → 2024 Patrick Esser et al. ★ → 2025 Black Forest Labs et al. ★ |
| ⑥ | Robin Rombach et al. | 2023 Lvmin Zhang et al. ★ |
| ⑦ | William Peebles et al. | 2024 Yi Jiang et al. ★ → 2025 Xiaokang Chen et al. ★ |

### 节点

| 年份 | 作者 | 角色 | 引用 | 简短标题 | 核验 |
| ---: | --- | --- | ---: | --- | :---: |
| 2015 | Jascha Sohl‐Dickstein et al. | ● 奠基 | 1417 | Deep Unsupervised Learning using … | — |
| 2019 | Yang Song et al. | ● 奠基 | 986 | Generative Modeling by Estimating… | — |
| 2020 | Ho, Jonathan et al. | ◉ 枢纽 | 5637 | Denoising Diffusion Probabilistic… | ✓ |
| 2020 | Yang Song et al. | ○ 其他 | 1274 | Score-Based Generative Modeling t… | ✓ |
| 2020 | Jiaming Song et al. | ○ 其他 | 102 | Denoising Diffusion Implicit Mode… | ✓ |
| 2021 | Prafulla Dhariwal et al. | ◉ 枢纽 | 2173 | Diffusion Models Beat GANs on Ima… | ✓ |
| 2021 | Alex Nichol et al. | ○ 其他 | 412 | Improved Denoising Diffusion Prob… | ⚠ |
| 2022 | Jonathan Ho et al. | ○ 其他 | 742 | Classifier-Free Diffusion Guidance | ✓ |
| 2022 | Tero Karras et al. | ○ 其他 | 308 | Elucidating the Design Space of D… | ⚠ |
| 2022 | Aditya Ramesh et al. | ◉ 枢纽 | 2286 | Hierarchical Text-Conditional Ima… | ✓ |
| 2022 | Robin Rombach et al. | ◉ 枢纽 | 13635 | High-Resolution Image Synthesis w… | ✓ |
| 2022 | Chitwan Saharia et al. | ◉ 枢纽 | 2106 | Photorealistic Text-to-Image Diff… | ✓ |
| 2023 | William Peebles et al. | ★ 前沿 | 1418 | Scalable Diffusion Models with Tr… | ✓ |
| 2023 | Lvmin Zhang et al. | ★ 前沿 | 3589 | Adding Conditional Control to Tex… | ✓ |
| 2024 | Patrick Esser et al. | ★ 前沿 | 86 | Scaling Rectified Flow Transforme… | ✓ |
| 2024 | Yi Jiang et al. | ★ 前沿 | 38 | Visual Autoregressive Modeling | ⚠ |
| 2025 | Black Forest Labs et al. | ★ 前沿 | 4 | FLUX.1 Kontext | ⚠ |
| 2025 | Xiaokang Chen et al. | ★ 前沿 | 10 | Janus-Pro | ⚠ |

### 连接（只画这些）

| 起点 | → | 终点 | 关系 | 箭头样式 | 核验 |
| --- | :---: | --- | --- | --- | :---: |
| Jascha Sohl‐Dickstein et al. 2015 | → | Ho, Jonathan et al. 2020 | builds-on | 细实线箭头 → | ✓ |
| Yang Song et al. 2019 | → | Yang Song et al. 2020 | builds-on | 细实线箭头 → | ✓ |
| Ho, Jonathan et al. 2020 | → | Jiaming Song et al. 2020 | builds-on | 细实线箭头 → | ✓ |
| Ho, Jonathan et al. 2020 | → | Alex Nichol et al. 2021 | builds-on | 细实线箭头 → | ⚠ |
| Ho, Jonathan et al. 2020 | → | Prafulla Dhariwal et al. 2021 | builds-on | 细实线箭头 → | ✓ |
| Alex Nichol et al. 2021 | → | Prafulla Dhariwal et al. 2021 | builds-on | 细实线箭头 → | ✓ |
| Yang Song et al. 2020 | → | Tero Karras et al. 2022 | builds-on | 细实线箭头 → | ⚠ |
| Prafulla Dhariwal et al. 2021 | → | Jonathan Ho et al. 2022 | builds-on | 细实线箭头 → | ✓ |
| Prafulla Dhariwal et al. 2021 | → | Robin Rombach et al. 2022 | builds-on | 细实线箭头 → | ✓ |
| Jonathan Ho et al. 2022 | → | Chitwan Saharia et al. 2022 | builds-on | 细实线箭头 → | ✓ |
| Prafulla Dhariwal et al. 2021 | → | Aditya Ramesh et al. 2022 | builds-on | 细实线箭头 → | ✓ |
| Robin Rombach et al. 2022 | → | William Peebles et al. 2023 | builds-on | 细实线箭头 → | ✓ |
| Robin Rombach et al. 2022 | → | Lvmin Zhang et al. 2023 | builds-on | 细实线箭头 → | ✓ |
| Robin Rombach et al. 2022 | → | Patrick Esser et al. 2024 | builds-on | 细实线箭头 → | ✓ |
| William Peebles et al. 2023 | → | Patrick Esser et al. 2024 | builds-on | 细实线箭头 → | ✓ |
| William Peebles et al. 2023 | → | Yi Jiang et al. 2024 | builds-on | 细实线箭头 → | ⚠ |
| Patrick Esser et al. 2024 | → | Black Forest Labs et al. 2025 | builds-on | 细实线箭头 → | ⚠ |
| Yi Jiang et al. 2024 | → | Xiaokang Chen et al. 2025 | builds-on | 细实线箭头 → | ⚠ |
| William Peebles et al. 2023 | → | Xiaokang Chen et al. 2025 | inspired-by | 虚线箭头 ⇢ | ⚠ |
| Ho, Jonathan et al. 2020 | → | Yang Song et al. 2020 | parallel | 点线·无箭头 ∥ | ‼ |
| Aditya Ramesh et al. 2022 | → | Chitwan Saharia et al. 2022 | parallel | 点线·无箭头 ∥ | ‼ |
| Patrick Esser et al. 2024 | → | Yi Jiang et al. 2024 | parallel | 点线·无箭头 ∥ | — |

### 图例

- 角色：● 奠基 / ◉ 枢纽 / ★ 前沿 / ○ 其他
- 颜色：橙＝前沿·核心创新·supersedes·输出；蓝＝builds-on 主干·枢纽；绿＝奠基；灰＝其他·未验证
- 核验：✓ 已用引用核验　⚠ 参考文献待索引　‼ 互引　∥ 并行　? 关系待确认

## 三、给作者的话（投喂前先做）

1. 把上面 7 条泳道〈待命名〉改成真实路线名（如 频域路线 / CLIP 特征路线 / 重建误差路线）。
2. 核对带 `?` 的关系标签与所有 ⚠ 边——它们是自动猜测/未验证，确认或修正后再出图。
3. 其余结构（节点、连接、颜色语义）已与 lineage.json 一致，请勿改动。
