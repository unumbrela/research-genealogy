# 扩散模型图像生成 发展历程

> 从非平衡热力学的理论奠基，到 Stable Diffusion / DALL·E 2 引爆文生图，再到 DiT/rectified flow 架构革命与 2024–25 的自回归·统一多模态新范式
> · 2015–2025 · 18 篇关键论文 · 22 条引用边经 OpenAlex / Semantic Scholar 校验（✓13 已验证 / ∥1 并行 / ‼2 互引 / ⚠6 参考文献待索引）
> · 由 [research-genealogy](https://github.com/unumbrela/research-genealogy) 生成（Claude 点名 + 脚本核验）

## 全景谱系树

`scripts/render_tree.py diffusion-models-lineage.json --no-color` 的实际输出
（左侧为年份轴，● 奠基 / ◉ 枢纽 / ★ 前沿，每条边带 ✓/⚠ 校验标记）：

```
      ╭──────────────────────────────────────────────────────────╮
      │ 扩散模型图像生成 (Diffusion Models for Image Generation) │
      │ 18 papers  ·  2015 → 2025                                │
      ╰──────────────────────────────────────────────────────────╯
      │
 2015 │  ● Jascha Sohl‐Dickstein et al.   █████░░ 1417
      │     “Deep Unsupervised Learning using Nonequilibrium Thermodynamics”
      │       生成模型长期在「表达力强」与「可解析采样/推断」之间二选一 ⇒ 借非平衡热力学：前向扩散+反向去噪
      │     │
 2020 │     └── ◉ Ho, Jonathan et al. ✓   ██████░ 5637
      │         “Denoising Diffusion Probabilistic Models”
      │           此前扩散思想的样本质量远不及 GAN，无人重视 ⇒ 用加权变分目标训练去噪扩散(DDPM)
      │         │
 2020 │         ├── ○ Jiaming Song et al. ✓   ███░░░░  102
      │         │   “Denoising Diffusion Implicit Models”
      │         │     DDPM 采样需模拟上百步马尔可夫链，太慢 ⇒ 提出非马尔可夫的确定性采样(DDIM)
      │         │
 2021 │         └── ○ Alex Nichol et al. ⚠   ████░░░  412
      │             “Improved Denoising Diffusion Probabilistic Models”
      │               原始 DDPM 的对数似然与采样效率欠佳 ⇒ 学习方差、改进噪声调度
      │             │
 2021 │             └── ◉ Prafulla Dhariwal et al. ✓   ██████░ 2173
      │                 “Diffusion Models Beat GANs on Image Synthesis”
      │                   扩散仍未在基准上全面超过 GAN ⇒ 改进架构 + classifier guidance，确立 SOTA
      │                   → builds-on: Ho, Jonathan et al.
      │                 │
 2022 │                 ├── ○ Jonathan Ho et al. ✓   █████░░  742
      │                 │   “Classifier-Free Diffusion Guidance”
      │                 │     依赖额外分类器，复杂且易失真 ⇒ 用有/无条件模型之差实现免分类器引导(CFG)
      │                 │   │
 2022 │                 │   └── ◉ Chitwan Saharia et al. ✓   ██████░ 2106
      │                 │       “Photorealistic Text-to-Image Diffusion Models…(Imagen)”
      │                 │         文生图语言理解不足 ⇒ 用冻结大语言模型(T5)做文本编码 + 级联扩散
      │                 │         ∥ parallel: Aditya Ramesh et al.（实为 Imagen 引用 DALL·E2）
      │                 │
 2022 │                 ├── ◉ Aditya Ramesh et al. ✓   ██████░ 2286
      │                 │   “Hierarchical Text-Conditional Image Generation with CLIP Latents”
      │                 │     如何把 CLIP 语义用于文生图 ⇒ 两阶段 unCLIP(DALL·E 2)
      │                 │
 2022 │                 └── ◉ Robin Rombach et al. ✓   ███████ 13635
      │                     “High-Resolution Image Synthesis with Latent Diffusion Models”
      │                       像素空间扩散昂贵 ⇒ 压到潜空间再扩散(LDM)，催生 Stable Diffusion
      │                     │
 2023 │                     ├── ★ William Peebles et al. ✓   █████░░ 1418
      │                     │   “Scalable Diffusion Models with Transformers (DiT)”
      │                     │     U-Net 扩展性受限 ⇒ Transformer 替换骨干，揭示 scaling 规律
      │                     │   │
 2024 │                     │   ├── ★ Patrick Esser et al. ✓   ███░░░░   86
      │                     │   │   “Scaling Rectified Flow Transformers…(SD3)”
      │                     │   │     高分辨率/文本对齐瓶颈 ⇒ rectified flow + 多模态 DiT(MMDiT)
      │                     │   │     → builds-on: Robin Rombach et al.
      │                     │   │   │
 2025 │                     │   │   └── ★ Black Forest Labs et al. ⚠   █░░░░░░    4
      │                     │   │       “FLUX.1 Kontext: Flow Matching for In-Context Editing”
      │                     │   │         rectified flow 一脉 ⇒ 原生上下文图像生成与编辑
      │                     │   │
 2024 │                     │   └── ★ Yi Jiang et al. ⚠   ███░░░░   38
      │                     │       “Visual Autoregressive Modeling…(VAR)”
      │                     │         自回归长期落后扩散 ⇒「下一尺度预测」由粗到细生成
      │                     │         ∥ parallel: Patrick Esser et al.（同期范式之争）
      │                     │       │
 2025 │                     │       └── ★ Xiaokang Chen et al. ⚠   ██░░░░░   10
      │                     │           “Janus-Pro: Unified Multimodal…”
      │                     │             理解与生成相互制约 ⇒ 解耦视觉编码 + 规模化
      │                     │             ⇢ inspired-by: William Peebles et al.
      │                     │
 2023 │                     └── ★ Lvmin Zhang et al. ✓   ██████░ 3589
      │                         “Adding Conditional Control…(ControlNet)”
      │                           难加空间条件 ⇒ 冻结原模型旁挂可训练副本，即插即用可控
      │
 2019 │  ● Yang Song et al.   █████░░  986
      │     “Generative Modeling by Estimating Gradients of the Data Distribution (NCSN)”
      │       概率密度需难解归一化常数 ⇒ 用 score matching 估梯度 + Langevin 采样
      │     │
 2020 │     └── ○ Yang Song et al. ✓   █████░░ 1274
      │         “Score-Based Generative Modeling through SDEs”
      │           两条线缺乏统一理论 ⇒ 用 SDE 统一 DDPM 与 score-based，给出概率流 ODE
      │           ∥ parallel: Ho, Jonathan et al.（实为 Score-SDE 引用 DDPM）
      │         │
 2022 │         └── ○ Tero Karras et al. ⚠   ████░░░  308
      │             “Elucidating the Design Space of Diffusion-Based Generative Models (EDM)”
      │               设计选择纠缠不清 ⇒ 解耦设计空间 + 更优采样器

      ● founder  ◉ hub  ★ frontier  ·  ├── builds-on  ├┈┈ inspired-by  ∥ parallel
      citations: ✓ 13 verified  ⚠ 8 to review   (run verify.py)
```

> **⚠ 关于引用数**：上图引用数取自 **OpenAlex 单条记录**。OpenAlex 会把同一篇论文的
> 预印本与正式版拆成多条记录、分摊引用，因此对经典论文**严重低估**——例如 DDIM 实际被引
> 数千次，这里只显示 102；VAR、EDM、Improved DDPM 同理。**请把引用数仅作量级参考**，谱系
> 的价值在于「谁建立在谁之上」的关系，而非这些数字。

## 发展历程

### 奠基（2015–2020）：两条独立的线汇成一条河

扩散模型有**两个独立源头**，2020 年才合流。

- **热力学线**：Sohl-Dickstein (2015) 借非平衡热力学提出——先用一条前向马尔可夫链把数据**逐步扩散成噪声**，再训练一个反向链一步步去噪。它解决的是生成模型长期的两难：要么表达力强但难采样/推断，要么可解析但太受限。但当时样本质量平平，几乎无人跟进。
- **分数线**：与之**并行**，Song & Ermon (2019) 的 NCSN 走另一条路——绕开难解的归一化常数，直接用 score matching 估计数据分布的**梯度(score)**，再用 Langevin 动力学采样。

转折点是 **Ho (2020) 的 DDPM**：用一个加权变分目标重新训练去噪扩散，**首次让扩散在图像质量上比肩 GAN**，真正引爆了这个方向。紧接着 **Song (2020) 的 Score-SDE** 用随机微分方程把"热力学线"和"分数线"**统一**起来（离散步 = SDE 的离散化），并给出概率流 ODE——两条河至此汇为一条，理论框架成型。（二者同年、相隔数月：本谱系将其标为 `parallel`(并行)，但严格说 Score-SDE 引用了 DDPM，故 `verify.py` 标记为 ‼ 互引——这是一处可改判为 builds-on 的关系。）

### 提速与提质（2020–2022）：让扩散真正可用

DDPM 虽好，但有两个硬伤——**采样太慢**、**还没全面赢 GAN**。三项工作分别攻克：

- **采样加速**：Song (2020) 的 **DDIM** 提出非马尔可夫的确定性采样，在保质量前提下把上百步压到几十步。
- **质量/似然**：Nichol (2021) 的 **Improved DDPM** 用学习方差、改噪声调度等简单改动兼顾样本质量与似然；**Dhariwal (2021) 的 "Beat GANs"** 则改进架构 + 引入 classifier guidance，在多项基准**正式超越 BigGAN**，确立扩散为新 SOTA。
- **引导方式**：Ho (2022) 的 **Classifier-Free Guidance (CFG)** 去掉了额外分类器的依赖，用有/无条件模型之差实现引导——这成为后续所有文生图模型**可控生成的标准开关**。

### 文生图爆发（2022）：三强并立

2022 年扩散从研究走向产品，三个标志性文生图系统几乎同时出现，构成本谱系最热闹的一层：

- **Rombach 的 LDM / Stable Diffusion**（引用 13635，全树最高）：先用自编码器把图像压到**潜空间**再扩散，大幅降算力、可跑高分辨率，并支持跨模态条件——开源后成为整个生态的地基。
- **Ramesh 的 DALL·E 2 / unCLIP**：两阶段——先由文本生成 CLIP 图像隐变量，再用扩散解码。
- **Saharia 的 Imagen**：直接用大型**冻结语言模型 (T5)** 做文本编码 + 级联扩散，主打语言理解深度。

DALL·E 2 (4月) 与 Imagen (5月) 是同期竞争工作，本谱系标 `parallel`；严格说 Imagen 引用了 DALL·E 2（`verify.py` 同样标 ‼ 互引）。这一层都站在 Dhariwal 的"Beat GANs"与 CFG 的肩膀上。

### 架构革命（2023–2024）：U-Net 退场，Transformer 登台

- **Peebles (2023) 的 DiT** 把扩散主干从 U-Net 换成 **Transformer**，揭示了可预测的 **scaling 规律**——这一步为后续所有大模型骨干铺路。
- **Zhang (2023) 的 ControlNet** 解决"预训练大模型难加空间条件"的痛点：冻结原模型、旁挂可训练副本注入边缘/姿态，**即插即用的可控生成**。
- **Esser (2024) 的 SD3** 把 rectified flow（直线化前向路径）与**多模态 DiT (MMDiT)** 结合并规模化，是 DiT 路线的集大成。

### 近两年前沿（2024–2025）：范式之争

主线扩散稳固之后，前沿出现**三个新方向**（这一段的节点引用边多为 ⚠——参考文献尚未被 OpenAlex/S2 索引，已诚实标记）：

- **Rectified flow 路线**：FLUX.1 Kontext (2025, Black Forest Labs) 沿 SD3 的 flow matching / rectified flow 一脉，主打**原生上下文图像生成与编辑**（FLUX.1[dev] 为开放权重，Kontext 旗舰版经 API 提供，并非完全开源）。
- **自回归反扑**：Jiang (2024) 的 **VAR** 提出"下一尺度预测"的视觉自回归，由粗到细生成，**质量首次反超扩散**（与 SD3 是同期的范式之争，标 `parallel`）。
- **统一多模态**：Chen (2025) 的 **Janus-Pro** 解耦视觉编码、扩大数据与模型规模，让单一模型同时增强多模态**理解与生成**——接续 VAR 的自回归思路，并受 DiT 启发。

趋势很清晰：**扩散主线 → Transformer 骨干 → rectified flow 与自回归两条新范式分庭抗礼 → 走向理解-生成统一的大一统模型**。

## 开放问题

1. **采样效率 vs 质量**：尽管 DDIM/EDM 一路提速，少步（1–4 步）高质量生成仍是活跃战场，蒸馏/一致性模型与 rectified flow 各执一词。
2. **范式未定**：扩散、rectified flow、视觉自回归（VAR/Janus-Pro）谁是终局尚无定论——VAR 在质量上反超，但生态与可控性仍以扩散为主。
3. **可控与一致性**：ControlNet 之后，多条件、长程一致、可编辑性（FLUX Kontext 主打的方向）仍未被很好统一。
4. **理解-生成统一的代价**：Janus-Pro 一类统一模型中，理解与生成任务相互制约，如何不靠复杂多阶段训练就两全，仍是开放问题。
5. **评测**：FID 等指标与人类偏好脱节日益严重，前沿模型的真实差距难以可靠衡量。

## 论文清单

| Year | Paper | Cites | Role | Citation |
| ---: | --- | ---: | --- | :---: |
| 2015 | [Sohl‐Dickstein et al. — Deep Unsupervised Learning using Nonequilibrium Thermodynamics](http://arxiv.org/abs/1503.03585) | 1417 | founder | — |
| 2019 | [Yang Song et al. — Generative Modeling by Estimating Gradients of the Data Distribution](http://arxiv.org/abs/1907.05600) | 986 | founder | — |
| 2020 | [Ho et al. — Denoising Diffusion Probabilistic Models](http://arxiv.org/abs/2006.11239) | 5637 | hub | ✓ |
| 2020 | [Yang Song et al. — Score-Based Generative Modeling through SDEs](http://arxiv.org/abs/2011.13456) | 1274 | other | ✓ |
| 2020 | [Jiaming Song et al. — Denoising Diffusion Implicit Models](http://arxiv.org/abs/2010.02502) | 102 | other | ✓ |
| 2021 | [Dhariwal et al. — Diffusion Models Beat GANs on Image Synthesis](http://arxiv.org/abs/2105.05233) | 2173 | hub | ✓ |
| 2021 | [Nichol et al. — Improved Denoising Diffusion Probabilistic Models](http://arxiv.org/abs/2102.09672) | 412 | other | ⚠ |
| 2022 | [Ho et al. — Classifier-Free Diffusion Guidance](http://arxiv.org/abs/2207.12598) | 742 | other | ✓ |
| 2022 | [Karras et al. — Elucidating the Design Space of Diffusion-Based Generative Models](http://arxiv.org/abs/2206.00364) | 308 | other | ⚠ |
| 2022 | [Ramesh et al. — Hierarchical Text-Conditional Image Generation with CLIP Latents](http://arxiv.org/abs/2204.06125) | 2286 | hub | ✓ |
| 2022 | [Rombach et al. — High-Resolution Image Synthesis with Latent Diffusion Models](https://doi.org/10.1109/cvpr52688.2022.01042) | 13635 | hub | ✓ |
| 2022 | [Saharia et al. — Photorealistic Text-to-Image Diffusion Models (Imagen)](http://arxiv.org/abs/2205.11487) | 2106 | hub | ✓ |
| 2023 | [Peebles et al. — Scalable Diffusion Models with Transformers (DiT)](https://doi.org/10.1109/iccv51070.2023.00387) | 1418 | frontier | ✓ |
| 2023 | [Zhang et al. — Adding Conditional Control to Text-to-Image Diffusion Models (ControlNet)](https://doi.org/10.1109/iccv51070.2023.00355) | 3589 | frontier | ✓ |
| 2024 | [Esser et al. — Scaling Rectified Flow Transformers for High-Resolution Image Synthesis (SD3)](http://arxiv.org/abs/2403.03206) | 86 | frontier | ✓ |
| 2024 | [Jiang et al. — Visual Autoregressive Modeling: Next-Scale Prediction (VAR)](https://doi.org/10.52202/079017-2694) | 38 | frontier | ⚠ |
| 2025 | [Black Forest Labs — FLUX.1 Kontext: Flow Matching for In-Context Image Generation and Editing](https://openalex.org/W4414682104) | 4 | frontier | ⚠ |
| 2025 | [Chen et al. — Janus-Pro: Unified Multimodal Understanding and Generation](https://openalex.org/W4406975803) | 10 | frontier | ⚠ |

---
*所有节点元数据取自 OpenAlex（2026-06）；Claude 用知识 + WebSearch 点名候选，再经脚本逐个解析为真实记录（"Qwen-Image Technical Report" 未解析到，已弃用而非编造）。引用边经 `verify.py` 校验，⚠ 表示 OpenAlex/S2 参考文献数据缺口（多为 2024–25 新论文），未强行声称。VAR / FLUX / Janus-Pro 的摘要尚未被索引，其问题/贡献据真实标题语义概括并已标注。*
