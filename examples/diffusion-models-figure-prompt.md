# 扩散模型发展历程 · 配图提示词与投喂指南

> 用于把 `diffusion-models-genealogy.md` 的优化内容画成一张**适合论文发表的科研流程图**。
> 版式：横向时间线 + 4 条分支泳道。风格对齐参考示例（白底、蓝+浅紫、橙色诚实性徽标、扁平矢量、细线箭头）。

---

## 一、要给图像生成模型提供的三样东西

把下面三块**一起**喂给图像模型（Nano Banana / Seedream / GPT-Image / Midjourney 等），正确率最高：

1. **提示词正文**（第二节，主体描述版式与风格）。
2. **结构清单**（第三节）——把"泳道 × 年代 × 节点 + 箭头关系"列成表，**贴在提示词后面**。图像模型最容易把多节点的连线画乱，给定显式结构能显著提升节点位置与箭头方向的正确率。
3. **风格/版式参考**：白底、蓝+浅紫主色、橙色强调，宽高比 **16:9 或 2:1（横图）**；如有，附上你那张"三段管线"参考图作为风格样例（"按这张图的配色与线条质感"）。

> 实操建议：
> - 图像模型常把**大量小字标签画糊**。两条路：① 提示词里强调"标签极少、字体清晰、英文模型名为主"；② **先让模型出"少字/无字的版式骨架"，再用 Figma / draw.io / PPT 补精确文字**——出版级图建议走这条。
> - 想要**可编辑矢量底稿**：直接 `python3 scripts/render_tree.py examples/diffusion-models.json --format drawio > diffusion.drawio`，导入 draw.io 调版式与配色，比纯图像生成更可控。
> - 想要**结构绝对正确**：把第三节结构清单当成"硬约束"，让图像模型只负责"美化排版"，不负责"决定连线"。

---

## 二、提示词正文（直接复制）

请生成一张**适合论文发表的科研流程图**，主题是"**扩散模型图像生成的发展历程（2011→2024）**"，强调**脉络清晰、引用可核验的科学严谨性**。

采用**从左到右的横向时间线布局**，顶部是一条**年代轴**：2011 · 2015 · 2019–2020 · 2021–2022 · 2023–2024。画面纵向分为 **4 条水平泳道**，每条泳道是一条技术路线，自上而下：

- **泳道① 分数 / SDE 路线**：Vincent(score matching) → NCSN → Score-SDE；
- **泳道② 扩散主干 + 采样加速**：Sohl-Dickstein(扩散奠基) → DDPM(引爆点，画成高亮枢纽) → DDIM → DPM-Solver++ → Consistency；
- **泳道③ 潜空间文生图**：VAE → VQ-VAE → LDM/Stable Diffusion，其右侧并排 DALL·E 2 与 Imagen 三个文生图模型图标；
- **泳道④ 引导·架构·可控·新范式**：classifier guidance(Dhariwal) → CFG → ；DiT 与 ControlNet 并列 → SD3(rectified flow)。

每个节点是一个**极简扁平模型图标 + 一个简短英文标签**（DDPM、DDIM、Score-SDE、NCSN、DPM-Solver++、Consistency、VAE、VQ-VAE、LDM/SD、DALL·E2、Imagen、CFG、DiT、ControlNet、SD3）。用**细线实箭头**沿泳道从左到右串联表示"在其基础上构建(builds-on)"；用**竖向虚线**连接同期并行的工作（如 LDM ∥ DALL·E2 ∥ Imagen，以及 DiT ∥ ControlNet）；用一条**橙色粗箭头**从扩散主干指向左下角的 GAN(BigGAN) 图标并标注"⇒ 超越/supersedes"。

在左端把 **Sohl-Dickstein(扩散框架)** 与 **Vincent(score)** 画成两个**起点锚标**；在 LDM 节点处用一个小小的"汇合"符号表示它**同时承接 DDPM 与 VQ-VAE 两条线**。

**橙色用于"真实 / 已核验"诚实性徽标**：在右下角放一个橙色小徽标"真实论文 · 引用经 OpenAlex/S2 核验 ✓ · Zero-hallucination"，并在已核验的箭头旁点缀极小的橙色 ✓。

整体风格**专业、清晰、矢量化科研插图质感**，画面干净、四条泳道层级分明、左右按年代对齐整齐。**白色背景，蓝色与浅紫色为主色，橙色仅用于"超越"箭头与"诚实性"徽标**。扁平简洁图标、细线箭头串联流程，避免过度装饰；**不要出现大段文字说明，仅保留极少量简短英文模型标签 + 极少中文路线名（分数路线 / 扩散主干 / 文生图 / 架构·可控）**。

---

## 三、结构清单（贴在提示词后，作为连线硬约束）

```
画布：横向 16:9，白底；顶部年代轴 2011 · 2015 · 2019 · 2020 · 2021 · 2022 · 2023 · 2024
四条水平泳道（上→下）：①分数/SDE  ②扩散主干+采样  ③潜空间文生图  ④引导·架构·可控

节点（泳道 / 年代 / 标签 / 角色）：
 ① 2011 Vincent(奠基)   2019 NCSN   2020 Score-SDE(理论总纲)
 ② 2015 Sohl-Dickstein(奠基)  2020 DDPM(枢纽,高亮)  2020 DDIM  2022 DPM-Solver++  2023 Consistency
 ③ 2013 VAE  2017 VQ-VAE  2022 LDM/Stable Diffusion(枢纽)  2022 DALL·E2  2022 Imagen
 ④ 2018 BigGAN(对照,左下)  2021 Dhariwal(classifier guidance)  2022 CFG
    2023 DiT  2023 ControlNet  2024 SD3(前沿,最右)

实箭头 = builds-on（细线，沿时间从左指向右）：
 Vincent→DDPM ; Vincent→NCSN ; NCSN→Score-SDE ; Sohl-Dickstein→DDPM ; Sohl-Dickstein→Score-SDE
 DDPM→DDIM ; DDPM→Dhariwal ; DDPM→LDM ; DDPM→Imagen
 DDIM→DPM-Solver++ ; DDIM→Consistency ; Score-SDE→DPM-Solver++ ; Score-SDE→Consistency
 Dhariwal→CFG ; CFG→Imagen
 VAE→VQ-VAE ; VQ-VAE→LDM ; Dhariwal→LDM
 LDM→DiT ; LDM→ControlNet ; LDM→SD3 ; DiT→SD3

虚线 = parallel（竖向，无方向）： DiT ∥ ControlNet ；（可选）LDM ∥ DALL·E2 ∥ Imagen
点线 = inspired-by： Dhariwal ┄→ DALL·E2
橙色粗箭头 = supersedes： Dhariwal/扩散主干 ⇒ BigGAN（标注"超越 GAN"）

橙色诚实性徽标（右下角）："真实论文 · 引用经 OpenAlex/S2 核验 ✓ · Zero-hallucination"
```

---

## 四、备选：更贴近"三段式"参考版（如果你想要更简洁）

若想最贴近你给的三段参考图，可把四泳道压成**三段横向**：
**① 奠基理论**（score matching · VAE · 热力学扩散）→ **② 核心突破与路线分化**（DDPM → Score-SDE / DDIM；LDM·DALL·E2·Imagen；classifier→CFG）→ **③ 近两年前沿**（DiT · ControlNet · Consistency · SD3）。
段间用细线箭头串联，橙色徽标与配色不变。提示词主体同上，只把"4 泳道"改成"3 段"、节点按段归并即可。
