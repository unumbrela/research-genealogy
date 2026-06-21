# 扩散模型图像生成 发展历程

> 从「学习去噪 = 估计 score」的理论火种，到 DDPM 引爆、连续时间统一、潜空间文生图三雄并起，再到 Transformer 骨干、精确可控、flow-matching 新范式，直至**自回归范式回潮与统一多模态生成** · **2011–2025 · 21 篇关键论文 · 5 条技术路线** · 引用边经 OpenAlex/S2 核验（**25 ✓ · 1 ∥ · 2 ⚠**，⚠ 为近年论文参考文献尚未被索引所致，下文说明）

## 全景谱系树

```
扩散模型图像生成 (Diffusion Models for Image Generation) · 21 papers · 2011 → 2025

分数 / SDE 路线
 2011 ● Vincent  score matching ↔ 去噪自编码器
 2019   └─ ○ Song & Ermon — NCSN  ✓     用 score+Langevin 采样，分数生成开山
 2020      └─ ○ Song et al. — Score-SDE ✓   SDE 统一 NCSN 与 DDPM（理论总纲）

潜空间路线
 2013 ● Kingma & Welling — VAE
 2017   └─ ○ van den Oord — VQ-VAE ✓        离散 latent，潜扩散的编码器

扩散主干
 2015 ● Sohl-Dickstein  非平衡热力学：扩散框架奠基
 2020   └─ ◉ Ho et al. — DDPM ✓  ← 引爆点（追平 GAN）  → builds-on: Vincent
        ├─ ○ Song et al. — DDIM ✓                确定性快速采样（提速 10–50×）
        │     └┄ 采样加速线 → DPM-Solver++ (2022) → Consistency Models (2023)
        └─ ◉ Dhariwal & Nichol (2021) ✓   classifier guidance 全面超越 GAN
              ⇒ supersedes: Brock — BigGAN (2018)
              │
              ├─ ★ Ho & Salimans — CFG (2022) ✓   classifier-free：文生图总开关
              │     └─ ★ Saharia et al. — Imagen ✓   T5+级联扩散+CFG，照片级
              ├─ ★ Rombach et al. — LDM / Stable Diffusion (2022) ✓
              │     → builds-on: VQ-VAE + DDPM（两根汇合）
              │     ├─ ★ Peebles & Xie — DiT (2023) ✓   Transformer 骨干 + scaling
              │     │     ├─ ★ Esser et al. — SD3 (2024) ✓   rectified flow 新范式
              │     │     └─ ★ Yi Jiang et al. — VAR (2024) ✓   自回归「下一分辨率」超越扩散
              │     │           └┄ inspired-by → ★ Janus-Pro (2025) ⚠   统一多模态生成
              │     └─ ★ Zhang et al. — ControlNet (2023) ✓   精确空间可控
              │          ∥ parallel: DiT
              └┄ inspired-by → ★ Ramesh et al. — DALL·E 2 (2022) ✓   unCLIP 路线

● founder  ◉ hub  ★ frontier  ·  ├─ builds-on  └┄ inspired-by  ∥ parallel  ⇒ supersedes
citations: ✓ 25 verified · ∥ 1 parallel · ⚠ 2 to review   (run verify.py)
```

> 节点角色：**●** 奠基 / **◉** 枢纽 / **★** 前沿；关系：`├─` builds-on、`└┄` inspired-by、`∥` parallel、`⇒` supersedes。每条 builds-on 边都经 `verify.py` 对照 OpenAlex/Semantic Scholar 的真实参考文献核验。完整渲染见 `render_tree.py examples/diffusion-models.json`。

## 发展历程

### 奠基（2011–2017）：三条根须各自生长
扩散模型不是凭空出现，它的三条根须早在草创期就已埋下，彼此独立、日后汇流。

**分数根**：**Vincent (2011)** 证明了一个朴素却深远的等价——训练去噪自编码器，本质就是在**匹配数据分布的 score（对数密度梯度）**，且无需昂贵的二阶导数。八年后，**Song & Ermon (2019) 的 NCSN** 把这一点变成可用的生成器：用 score matching 估计梯度、用 Langevin 动力学采样，并以**多尺度噪声扰动**解决低密度区 score 不准的难题——分数生成模型的开山之作。

**潜空间根**：**Kingma & Welling (2013) 的 VAE** 用重参数化让带连续隐变量的模型可直接 SGD 训练；**van den Oord (2017) 的 VQ-VAE** 进一步给出**离散 latent**、避免后验坍塌，为日后"先把图像压进紧凑 latent、再在其上做扩散"提供了编码器。

**扩散根**：**Sohl-Dickstein et al. (2015)** 从非平衡热力学借来核心想法——**前向逐步加噪把结构"扩散"成纯噪声，再学反向逐步去噪还原**——首次给出既灵活又可精确处理的扩散式生成模型。但受限于训练目标与算力，它沉睡了整整五年。

### 引爆与统一（2020）：DDPM 点火，Score-SDE 立纲
**Ho et al. (2020) 的 DDPM** 是整条路线的引爆点：在 Sohl-Dickstein 框架（builds-on）之上、借 Vincent 的 score 视角（builds-on ✓），把训练目标简化成一个**加权去噪回归损失**——优雅、稳定、好训，**第一次让扩散在图像质量上追平 GAN**。沉睡的框架被唤醒，此后几乎所有分支都从 DDPM 这个枢纽（◉）长出。

同年，**Song et al. (2020) 的 Score-SDE** 立起**理论总纲**：用随机微分方程把离散步的 DDPM 与分数匹配 **统一**成连续时间过程（NCSN→Score-SDE，builds-on ✓），给出 reverse-time SDE、**概率流 ODE** 采样与精确似然——它既收束了分数根，又成为日后快速采样与少步生成的数学地基。

### 采样加速线（2020→2023）：从上千步到几步
扩散好用但慢——DDPM 出一张图要模拟上千步。这条线专治"慢"：
- **Song et al. (2020) 的 DDIM**：构造与 DDPM 共享训练目标的**非马尔可夫确定性采样**，可大幅跳步、提速 10–50×，并让 latent 可插值、采样可复现（builds-on DDPM ✓）。
- **Lu et al. (2022) 的 DPM-Solver++**：把带引导采样建模成**高阶扩散 ODE 求解** + 多步稳定化，把高质量采样压到约 15–20 步（builds-on Score-SDE ✓；builds-on DDIM 为真实引用，但其 2025 期刊重印记录在 OpenAlex 参考文献缺失，故标 ⚠，见下）。
- **Song et al. (2023) 的 Consistency Models**：学习把概率流 ODE 轨迹上**任意点直接映射回起点**，支持**一步/少步生成**且可独立训练（builds-on Score-SDE ✓）——把"加速"推到新范式。

### 引导线（2021→2022）：CFG 成为文生图总开关
- **Dhariwal & Nichol (2021)**：通过架构消融 + **classifier guidance**（用分类器梯度在保真↔多样间权衡），首次让扩散在 ImageNet 上 FID **全面超越 BigGAN**——树上一条 `⇒ supersedes` 指向 **Brock et al. (2018, BigGAN)**，这正是扩散要跨过的 GAN 标杆（经核验是 Dhariwal 的真实引用 ✓）。
- **Ho & Salimans (2022) 的 Classifier-Free Guidance**：联合训练有/无条件模型、用二者之差放大条件信号，**无需任何分类器**即可调节保真↔多样（builds-on Dhariwal ✓）。CFG 看似小技巧，却成为**此后几乎所有文生图模型的标准开关**——下一段三雄无一例外。

### 潜空间文生图三雄（2022）：把扩散交到大众手里
2022 年，三个几乎同期、互相独立的工作把文生图推向爆发：
- **Rombach et al. (LDM / Stable Diffusion)**：把扩散搬进**预训练自编码器的潜空间**、用 cross-attention 注入文本条件，大幅降本提分辨率。这里**两根汇合**——它同时 builds-on DDPM（✓）与潜空间根的 VQ-VAE（✓）；开源的 SD 让文生图走向大众。
- **Saharia et al. (Imagen)**：用**大型冻结文本编码器 (T5) + 级联像素扩散 + CFG**，达到空前的照片级真实感与文本对齐（builds-on CFG / DDPM ✓），印证"大语言模型理解 + 扩散生成"的威力。
- **Ramesh et al. (DALL·E 2)**：走 **unCLIP** 两阶段路线（文本→CLIP 图像 embedding→扩散解码），多样性强、支持零样本编辑；它在概念上受引导式扩散启发（`└┄ inspired-by` Dhariwal ✓）。

> 这三者同期、互不隶属，彼此只有少量"相关工作"引用——本质是**并行**的三种文生图解法。

### 近两年前沿（2023–2024）：骨干、可控、新范式
- **架构骨干 → Peebles & Xie (2023, DiT)**：用 **Transformer 替换 U-Net** 在 latent patch 上做扩散，给出"算力越大、FID 越低"的清晰 **scaling 律**（builds-on LDM ✓），直接成为 SD3、Sora 的骨干选择。
- **精确可控 → Zhang et al. (2023, ControlNet)**：冻结 SD、旁路可训练副本注入边缘/姿态/深度等空间条件，让生成"指哪打哪"（builds-on LDM ✓）。DiT 与 ControlNet 同期独立、互不引用，是一对 **∥ parallel**（架构 vs 可控两条正交努力）。
- **新范式 → Esser et al. (2024, SD3 / Rectified Flow)**：用 **rectified flow（直线化的 flow matching）** 替代扩散的随机加噪路径、配**多模态 MM-DiT** 骨干（builds-on DiT / LDM ✓）——代表 2024 起"flow matching 取代/统一扩散"的新方向。
- **自回归回潮 → Yi Jiang et al. (2024, VAR)**：把图像自回归重定义为**"由粗到细的 next-scale（下一分辨率）预测"**，而非 raster-scan 逐 token——首次让**自回归模型在 ImageNet 上反超扩散**，并展现 GPT 式 scaling 律（builds-on VQ-VAE 的离散 tokenizer + DiT ✓，并把 SD3 当作要超越的扩散基线）。这把"扩散 vs 自回归"重新摆上桌面。
- **统一多模态生成 → Janus-Pro (2025)**：沿 VAR 开的自回归路线（`└┄ inspired-by`），用**解耦视觉编码 + 自回归框架**把"看图(理解)"与"画图(生成)"统一进单一多模态模型并做规模扩展——指向 2025 的"统一多模态生成"前沿。

> **关于"2026 最新"**：截至 2026-06，OpenAlex / Semantic Scholar **尚未索引到有分量的 2026 图像生成里程碑**（新论文有数月至一年的索引与引用滞后，检索 2026 只返回零引用的离题结果）。本工具的底线是**只收录可检索、可核验的真实论文，绝不为"凑年份"杜撰**——因此谱系当前最新到 **2025（Janus-Pro）**。若你手上有具体的 2026 论文（标题 / arXiv id），告诉我，我可精确拉取并接入。

### 诚实性说明（核验全景）
本谱系 28 条关系：**25 条 builds-on/supersedes/inspired-by 已核验为真实引用、1 条 parallel、仅 2 条 ⚠**。这一高核验率部分来自工具本轮升级的**重复记录 / 跨源和解**：
- OpenAlex 常把同一篇论文存成多个 work-id，早期 BigGAN、Sohl-Dickstein、NCSN 等被引用的记录 id 与节点不一致 → `verify.py` 现按**归一化标题/DOI**自动和解，无需手工对齐即转 ✓；
- VQ-VAE、Imagen、CFG、**VAR** 等论文的 OpenAlex 参考文献稀疏/缺失时，自动**回退 Semantic Scholar** 取参考文献核验（VAR 的 builds-on VQ-VAE / DiT 即由此确认）；
- 两处遗留 **⚠**，都不是杜撰、而是**索引滞后**：**① DPM-Solver++ builds-on DDIM**——真实引用，但其 OpenAlex 记录是 2025 期刊**重印**版、参考文献缺失，S2 keyless 池又被限流；**② Janus-Pro(2025) 的 inspired-by 来源**——这篇很新的论文在 OpenAlex 与 S2 中**都还没有参考文献列表**，故其谱系关系标为 `inspired-by` 并**如实保留 ⚠**，未强行断言引用。这正是 research-genealogy 的底线：**箭头可信，靠的是数据而非记忆**；越靠近前沿，⚠ 越是诚实的"数据未到"而非"作者瞎编"。

（另注：OpenAlex 对 DDPM 摘要被无关仓库 README 污染、对 DDIM/Consistency/SD3 引用数因重复记录而低估——前者摘要已据引用它的论文据实改写，后者引用条仅作视觉参考，节点 id 与引用边均真实。）

### 开放问题
1. **少步生成的质量天花板**：Consistency / 蒸馏已把采样压到几步乃至一步，但少步下的多样性、细节与文本对齐能否追平多步，仍未解决。
2. **三种范式之争（扩散 / flow matching / 自回归）**：SD3 的 rectified flow 用直线路径换效率，VAR 又让自回归"下一分辨率"反超扩散——扩散、flow matching、自回归三条路线谁主沉浮，或如何融合，是 2024 起最大的范式之争。
3. **统一多模态生成**：Janus-Pro 等把"理解 + 生成"塞进单一自回归模型，但生成质量与专用扩散/文生图模型相比仍有差距，统一架构能否同时做到"看得懂"和"画得好"尚无定论。
4. **可控性的统一接口**：ControlNet 之后条件适配器爆发，如何把空间/语义/风格/主体条件**统一、可组合**而非各做各的，尚无定论。
5. **scaling 律向高维模态外推**：DiT 的 scaling 在图像上清晰，但视频 / 3D / 4D 等高维模态下的数据-算力-架构最优配比仍待验证。
6. **理论回填**：Score-SDE 给了优雅的连续时间框架，但 guidance、潜空间压缩、rectified flow 等"工程加分项"尚未完全纳入统一理论。

## 论文清单

| Year | Paper | Cites | Role | Citation |
| ---: | --- | ---: | --- | :---: |
| 2011 | [Pascal Vincent — A Connection Between Score Matching and Denoising Autoencoders](https://doi.org/10.1162/neco_a_00142) | 979 | founder | — |
| 2013 | [Kingma, Welling — Auto-Encoding Variational Bayes (VAE)](http://arxiv.org/abs/1312.6114) | 15628 | founder | — |
| 2015 | [Sohl-Dickstein et al. — Deep Unsupervised Learning using Nonequilibrium Thermodynamics](http://arxiv.org/abs/1503.03585) | 1417 | founder | — |
| 2017 | [van den Oord et al. — Neural Discrete Representation Learning (VQ-VAE)](http://arxiv.org/abs/1711.00937) | 1969 | other | ✓ |
| 2018 | [Brock et al. — Large Scale GAN Training (BigGAN)](http://arxiv.org/abs/1809.11096) | 1786 | founder | — |
| 2019 | [Song, Ermon — Generative Modeling by Estimating Gradients of the Data Distribution (NCSN)](http://arxiv.org/abs/1907.05600) | 986 | other | ✓ |
| 2020 | [Ho et al. — Denoising Diffusion Probabilistic Models (DDPM)](http://arxiv.org/abs/2006.11239) | 5637 | hub | ✓ |
| 2020 | [J. Song et al. — Denoising Diffusion Implicit Models (DDIM)](http://arxiv.org/abs/2010.02502) | 102\* | other | ✓ |
| 2020 | [Y. Song et al. — Score-Based Generative Modeling through SDEs (Score-SDE)](http://arxiv.org/abs/2011.13456) | 1274 | other | ✓ |
| 2021 | [Dhariwal, Nichol — Diffusion Models Beat GANs on Image Synthesis](http://arxiv.org/abs/2105.05233) | 2173 | hub | ✓ |
| 2022 | [Ho, Salimans — Classifier-Free Diffusion Guidance (CFG)](http://arxiv.org/abs/2207.12598) | 742 | frontier | ✓ |
| 2022 | [Rombach et al. — Latent Diffusion Models (Stable Diffusion)](https://doi.org/10.1109/cvpr52688.2022.01042) | 13635 | frontier | ✓ |
| 2022 | [Ramesh et al. — CLIP-Latent Text-to-Image (DALL·E 2)](http://arxiv.org/abs/2204.06125) | 2286 | frontier | ✓ (inspired-by) |
| 2022 | [Saharia et al. — Photorealistic Text-to-Image with Deep Language Understanding (Imagen)](http://arxiv.org/abs/2205.11487) | 2106 | frontier | ✓ |
| 2022 | [Lu et al. — DPM-Solver++: Fast Solver for Guided Sampling](https://doi.org/10.1007/s11633-025-1562-4) | 99\* | frontier | ⚠ |
| 2023 | [Peebles, Xie — Scalable Diffusion Models with Transformers (DiT)](https://doi.org/10.1109/iccv51070.2023.00387) | 1418 | frontier | ✓ |
| 2023 | [Zhang et al. — Adding Conditional Control to T2I Diffusion (ControlNet)](http://arxiv.org/abs/2302.05543) | 3589 | frontier | ✓ ∥ |
| 2023 | [Y. Song et al. — Consistency Models](http://arxiv.org/abs/2303.01469) | 26\* | frontier | ✓ |
| 2024 | [Esser et al. — Scaling Rectified Flow Transformers (SD3)](http://arxiv.org/abs/2403.03206) | 86\* | frontier | ✓ |
| 2024 | [Jiang et al. — Visual Autoregressive Modeling: Next-Scale Prediction (VAR)](http://arxiv.org/abs/2404.02905) | 38\* | frontier | ✓ |
| 2025 | [Chen et al. — Janus-Pro: Unified Multimodal Understanding and Generation](http://arxiv.org/abs/2501.17811) | 10\* | frontier | ⚠ |

> \* DDIM / Consistency / SD3 / VAR / Janus-Pro / DPM-Solver++ 的引用数被 OpenAlex 因重复记录或索引滞后低估（真实影响远高于此）；此处只作视觉参考，节点身份与引用边均真实可核验。

---

*本报告由 [research-genealogy](https://github.com/unumbrela/research-genealogy) skill 生成：草稿管线（多遍检索 + 引用雪球 + 领域内打分 + 传递归约）产出于 OpenAlex 真实元数据，经人工精炼（补入 NCSN / DDIM / CFG / Consistency / Imagen / SD3 / VAR / Janus-Pro、按真实摘要改写、关系重标）并以 `verify.py`（重复记录 / Semantic Scholar 跨源和解）对照真实引用核验。数据快照：2026-06。*
