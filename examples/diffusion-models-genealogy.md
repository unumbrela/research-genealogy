# 扩散模型图像生成 发展历程

> 从「学习去噪 = 估计 score」的理论火种，到统一框架、潜空间提效、文本生图爆发、再到 Transformer 骨干与可控生成 · 2011–2025 · 14 篇关键论文 · 引用边经 OpenAlex 核验（13 ✓ / 2 ⚠，⚠ 均为 OpenAlex 缺参考文献所致，下文说明）

## 全景谱系树

```
      ╭──────────────────────────────────────────────────────────╮
      │ 扩散模型图像生成 (Diffusion Models for Image Generation) │
      │ 14 papers  ·  2011 → 2025                                │
      ╰──────────────────────────────────────────────────────────╯
      │
 2011 │  ● Pascal Vincent   █████░░  979
      │     “A Connection Between Score Matching and Denoising Autoencoders”
      │       score matching 需二阶导数、代价高，去噪自编码器又缺概率解释
      │ 
 2013 │  ● Diederik P. Kingma, Max Welling   ███████ 15628
      │     “Auto-Encoding Variational Bayes” (VAE)
      │       含连续隐变量、后验难解的有向概率模型如何高效学习
      │     │
 2017 │     └── ○ Aäron van den Oord et al. ⚠   █████░░ 1969   (VQ-VAE)
      │         “Neural Discrete Representation Learning”
      │           连续隐变量易后验坍塌，难学有用的离散表示
      │ 
 2015 │  ● Jascha Sohl-Dickstein et al.   █████░░ 1417   ← 奠基：扩散框架
      │     “Deep Unsupervised Learning using Nonequilibrium Thermodynamics”
      │       既灵活又可精确学习/采样的生成模型难以兼得
      │     │
 2020 │     ├── ◉ Jonathan Ho et al. ✓   ██████░ 5637   ← DDPM：引爆点
      │     │   “Denoising Diffusion Probabilistic Models”
      │     │     → builds-on: Pascal Vincent
      │     │   │
 2021 │     │   ├── ○ Prafulla Dhariwal, Alex Nichol ✓   ██████░ 2173
      │     │   │   “Diffusion Models Beat GANs on Image Synthesis”
      │     │   │     ⇒ supersedes: Andrew Brock et al. (BigGAN)
      │     │   │   │
 2022 │     │   │   ├── ◉ Robin Rombach et al. ✓   ███████ 13635   ← LDM / Stable Diffusion
      │     │   │   │   “High-Resolution Image Synthesis with Latent Diffusion Models”
      │     │   │   │     → builds-on: Aäron van den Oord et al.
      │     │   │   │     → builds-on: Jonathan Ho et al.
      │     │   │   │     ∥ parallel: Aditya Ramesh et al.
      │     │   │   │   │
 2023 │     │   │   │   ├── ★ William Peebles, Saining Xie ✦NEW ✓   █████░░ 1418   (DiT)
      │     │   │   │   │   “Scalable Diffusion Models with Transformers”
      │     │   │   │   │
 2023 │     │   │   │   ├── ★ Lvmin Zhang et al. ✦NEW ✓   ██████░ 3589   (ControlNet)
      │     │   │   │   │   “Adding Conditional Control to Text-to-Image Diffusion Models”
      │     │   │   │   │
 2025 │     │   │   │   └── ★ Cheng Lu et al. ✦NEW ✓   ███░░░░   99   (DPM-Solver++)
      │     │   │   │       “DPM-Solver++: Fast Solver for Guided Sampling…”
      │     │   │   │         → builds-on: Yang Song et al.
      │     │   │   │
 2022 │     │   │   └┈┈ ◉ Aditya Ramesh et al. ⚠   ██████░ 2286   (DALL·E 2)
      │     │   │       “Hierarchical Text-Conditional Image Generation with CLIP Latents”
      │     │   │
 2022 │     │   └── ○ Chitwan Saharia et al. ✓   █████░░ 1637   (SR3)
      │     │       “Image Super-Resolution via Iterative Refinement”
      │     │
 2020 │     └── ○ Yang Song et al. ✓   █████░░ 1274   ← 理论总纲：Score-SDE
      │         “Score-Based Generative Modeling through Stochastic Differential Equations”
      │ 
 2018 │  ● Andrew Brock et al.   █████░░ 1786   (BigGAN：被超越的标杆)
      │     “Large Scale GAN Training for High Fidelity Natural Image Synthesis”

      ● founder  ◉ hub  ★ frontier  ·  ├── builds-on  ├┈┈ inspired-by  ∥ parallel
      citations: ✓ 13 verified  ⚠ 2 to review   (run verify.py)
```

> 左侧为**年份轴**，节点角色：**●** 奠基 / **◉** 枢纽 / **★** 前沿；分支关系：`├──` builds-on、`├┈┈` inspired-by、`∥` parallel、`⇒` supersedes。每条 builds-on 边都经 `verify.py` 对照 OpenAlex 真实参考文献核验。

## 发展历程

### 奠基（2011–2015）：把"学习去噪"接上"概率生成"
扩散模型并非凭空出现，它的两条理论根须早在深度生成模型的草创期就已埋下。**Vincent (2011)** 证明了一个看似朴素却影响深远的等价关系：训练一个去噪自编码器，本质上就是在**匹配数据分布的 score（对数密度的梯度）**——这把"学会去噪"和"估计概率分布"划上了等号，且无需计算昂贵的二阶导数。与此并行，生成模型的另一条主线是隐变量模型：**Kingma & Welling (2013)** 的 VAE 用重参数化技巧让带连续隐变量的模型可以直接用 SGD 训练，奠定了"在隐空间里做生成"的范式——这条线后来会以意想不到的方式与扩散汇合。

真正点亮扩散框架的是 **Sohl-Dickstein et al. (2015)**。他们从非平衡热力学借来一个想法：用一个**前向过程逐步往数据里加噪、把结构慢慢"扩散"成纯噪声**，再训练一个**反向过程一步步去噪、把结构恢复回来**。这首次给出了一个**既足够灵活、又能精确学习与采样**的扩散式生成模型。但受限于当时的训练目标与算力，它的样本质量远不及同期的 GAN，沉寂了整整五年。

### 转折：DDPM 引爆（2020）
**Ho et al. (2020)** 的 DDPM 是整条路线的引爆点。它在 Sohl-Dickstein 框架（builds-on）之上，借 Vincent (2011) 的 score 视角（builds-on，✓ 已核验），把训练目标简化成一个**加权的去噪回归损失**——优雅、稳定、好训。结果是扩散模型**第一次在图像生成质量上追平 GAN**。沉睡的框架被唤醒，此后所有分支几乎都从 DDPM 这个枢纽（◉）长出。

紧接着，**Song et al. (2020)** 的 Score-SDE 提供了**理论总纲**：用随机微分方程把离散步的 DDPM 和分数匹配(NCSN)统一成**连续时间过程**，给出 reverse-time SDE、概率流 ODE 采样与精确似然——它从 Sohl-Dickstein 的扩散框架分出（builds-on，✓），日后又成为快速采样器的数学地基。

### 路线分化（2021–2022）：从"能用"到"好用、便宜、可控"
DDPM 之后，领域沿三条可辨认的路线展开：

- **保真路线 → Dhariwal & Nichol (2021)**：通过架构消融 + **classifier guidance**（用分类器梯度在保真与多样性间权衡），让扩散在 ImageNet 上 FID **全面超越 BigGAN**。这里树上有一条 `⇒ supersedes` 边指向 **Brock et al. (2018, BigGAN)**——它正是扩散要超越的 GAN 标杆，这条"超越"关系经核验是 Dhariwal 论文里的真实引用（✓）。
- **提效路线 → Rombach et al. (2022, LDM / Stable Diffusion)**：像素空间扩散训练要数百 GPU 天，太贵。LDM 把扩散搬进**预训练自编码器的潜空间**，并用 **cross-attention 注入文本条件**，一举把成本打下来、把分辨率提上去。注意这里**两条根须在此汇合**：它同时 builds-on DDPM（✓）和来自 VAE→VQ-VAE 线的 **van den Oord (2017)**（✓）——潜空间扩散正是"隐变量生成"与"扩散"的合流。开源的 Stable Diffusion 让文本生图走向大众。
- **条件化路线 → Saharia et al. (2022, SR3)**：把 DDPM 用于**以低分图为条件**的迭代去噪超分，人眼欺骗率近 50%，开启扩散做 image-to-image 的范式（builds-on DDPM，✓）。

与 LDM **并行（∥ parallel）**的是 **Ramesh et al. (2022, DALL·E 2)**：走 unCLIP 两阶段路线（先由文本生成 CLIP 图像 embedding、再用扩散解码器成图）。它与 Stable Diffusion 是同期、互不隶属的两种文本生图解法，故标为 parallel；同时它在概念上受 Dhariwal 的引导式扩散启发（`├┈┈ inspired-by`）。

### 近两年前沿（2023–2025）：骨干、可控、提速
扩散图像生成的"基本盘"在 2022 年已基本成型，近两年的前沿主要在三个方向上把它推向工业化：

1. **架构骨干 → Peebles & Xie (2023, DiT)**：用 **Transformer 替换 U-Net** 在 latent patch 上做扩散，证明了"**算力越大、FID 越低**"的清晰 scaling 规律。这条 scaling 法则直接催生了 SD3、Sora 等后续大模型的骨干选择（builds-on LDM，✓）。
2. **精确可控 → Zhang et al. (2023, ControlNet)**：纯文本 prompt 控不住空间结构。ControlNet **冻结预训练 Stable Diffusion、旁路一个可训练副本**注入边缘/姿态/深度等条件，让生成"指哪打哪"，催生海量可控生图应用（builds-on LDM，✓）。
3. **采样提速 → Lu et al. (DPM-Solver++)**：扩散采样动辄上百步。DPM-Solver++ 把带引导采样建模成**高阶扩散 ODE 求解**并做多步稳定化，把高质量采样压到约 15–20 步。它同时 builds-on LDM 与 **Song 的 Score-SDE**（✓）——理论总纲在此结出工程果实。

### 关于两处 ⚠（诚实性说明）
本谱系 16 条关系中 13 条 builds-on/supersedes 已核验为真实引用、1 条 parallel，**仅 2 条标 ⚠**，且二者都不是"存疑的杜撰"，而是 **OpenAlex 元数据缺失**所致：

- **VQ-VAE (van den Oord 2017)** 在 OpenAlex 中的 `referenced_works` 为**空**，因此"VQ-VAE builds-on VAE"这条本属常识的引用无法被自动核验；
- **DALL·E 2 (Ramesh 2022)** 同样在 OpenAlex 中**没有参考文献列表**，故其 inspired-by 边无法核验。

工具按设计**如实保留 ⚠ 标记**而非强行"洗白"——这正是 research-genealogy 的核心原则：**箭头可信，靠的是数据而非记忆**。（精炼时另修复了 3 条因 OpenAlex 重复记录导致 id 不一致的"假未核验"边：BigGAN、Sohl-Dickstein 被引用的记录 id 与节点 id 不同，对齐后即转为 ✓。）

### 开放问题
1. **采样步数 vs. 质量的极限**：DPM-Solver++ 已压到 ~15 步，蒸馏/一致性模型在追求"几步甚至一步"成图，但少步采样下的多样性与细节保真仍是开放问题。
2. **可控性的统一接口**：ControlNet 之后涌现大量条件适配器，如何把空间/语义/风格条件统一、可组合，而非各做各的，尚无定论。
3. **DiT scaling 的天花板**：Transformer 骨干带来清晰 scaling 律，但数据、算力、架构三者的最优配比，以及视频/3D 等高维模态下是否同样成立，仍待验证。
4. **理论与实践的回填**：Score-SDE 给了优雅的连续时间框架，但 guidance、潜空间压缩等"工程加分项"尚未完全纳入统一理论。

## 论文清单

| Year | Paper | Cites | Role | Citation |
| ---: | --- | ---: | --- | :---: |
| 2011 | [Pascal Vincent — A Connection Between Score Matching and Denoising Autoencoders](https://doi.org/10.1162/neco_a_00142) | 979 | founder | — |
| 2013 | [Kingma, Welling — Auto-Encoding Variational Bayes (VAE)](http://arxiv.org/abs/1312.6114) | 15628 | founder | — |
| 2015 | [Sohl-Dickstein et al. — Deep Unsupervised Learning using Nonequilibrium Thermodynamics](http://arxiv.org/abs/1503.03585) | 1417 | founder | — |
| 2017 | [van den Oord et al. — Neural Discrete Representation Learning (VQ-VAE)](http://arxiv.org/abs/1711.00937) | 1969 | other | ⚠ |
| 2018 | [Brock et al. — Large Scale GAN Training (BigGAN)](http://arxiv.org/abs/1809.11096) | 1786 | founder | — |
| 2020 | [Ho et al. — Denoising Diffusion Probabilistic Models (DDPM)](http://arxiv.org/abs/2006.11239) | 5637 | hub | ✓ |
| 2020 | [Song et al. — Score-Based Generative Modeling through SDEs](http://arxiv.org/abs/2011.13456) | 1274 | other | ✓ |
| 2021 | [Dhariwal, Nichol — Diffusion Models Beat GANs on Image Synthesis](http://arxiv.org/abs/2105.05233) | 2173 | other | ✓ |
| 2022 | [Rombach et al. — Latent Diffusion Models (Stable Diffusion)](https://doi.org/10.1109/cvpr52688.2022.01042) | 13635 | hub | ✓ |
| 2022 | [Ramesh et al. — Text-Conditional Image Generation with CLIP Latents (DALL·E 2)](http://arxiv.org/abs/2204.06125) | 2286 | hub | ⚠ |
| 2022 | [Saharia et al. — Image Super-Resolution via Iterative Refinement (SR3)](https://doi.org/10.1109/tpami.2022.3204461) | 1637 | other | ✓ |
| 2023 | [Peebles, Xie — Scalable Diffusion Models with Transformers (DiT)](https://doi.org/10.1109/iccv51070.2023.00387) | 1418 | frontier | ✓ |
| 2023 | [Zhang et al. — Adding Conditional Control to T2I Diffusion (ControlNet)](http://arxiv.org/abs/2302.05543) | 3589 | frontier | ✓ |
| 2025 | [Lu et al. — DPM-Solver++: Fast Solver for Guided Sampling](https://doi.org/10.1007/s11633-025-1562-4) | 99 | frontier | ✓ |

---

*本报告由 [research-genealogy](https://github.com/unumbrela/research-genealogy) skill 生成：草稿管线（多遍检索 + 引用雪球 + 领域内打分 + 传递归约）产出于 OpenAlex 真实元数据，经人工精炼（剪枝、按真实摘要改写、关系重标、前沿补全）并以 `verify.py` 对照真实引用核验。OpenAlex 数据快照：2026-06。*
