# AI4Reaction（AI 驱动的化学反应预测）发展历程

> 用机器学习/AI 预测化学反应——前向产物预测、逆合成规划、产率预测，直至自主化学实验
> · 1995–2025 · 15 篇关键论文 · 引用边均经 OpenAlex 验证（✓17 / ⚠2 诚实标记）
> · 由 [research-genealogy](https://github.com/unumbrela/research-genealogy) 生成

## 全景谱系树

```
      ╭──────────────────────────────────────────────────────────╮
      │ AI4Reaction（AI 驱动的化学反应预测 / 逆合成 / 自主化学） │
      │ 15 papers  ·  1995 → 2025                                │
      ╰──────────────────────────────────────────────────────────╯
      │
 1995 │  ● Hiroko Satoh et al.   ████░░░  127
      │     “SOPHIA, a Knowledge Base-Guided Reaction Prediction System - Utilization of a Knowledge Base…”
      │       反应预测长期依赖人工编写规则的专家系统，知识获取是最大瓶颈 ⇒ SOPHIA：从反应数据库自动导出…
      │     │
 2011 │     └── ○ Matthew A. Kayala et al. ✓   ████░░░  211
      │         “Learning to Predict Chemical Reactions”
      │           反应预测的三种途径（物理定律/规则系统/归纳学习）中，机器学习路线尚未建立 ⇒ 首批用统计…
      │         │
 2017 │         ├── ○ Connor W. Coley et al. ✓   █████░░  816
      │         │   “Prediction of Organic Reaction Outcomes Using Machine Learning”
      │         │     合成设计软件发展40年仍未普及——模板推荐的反应在实验室常常失败 ⇒ 从反应数据库学习给…
      │         │     ⇢ inspired-by: David Rogers et al.
      │         │   │
 2019 │         │   ├── ◉ Philippe Schwaller et al. ✓   █████░░  852
      │         │   │   “Molecular Transformer: A Model for Uncertainty-Calibrated Chemical Reaction Pred…”
      │         │   │     前向反应预测仍依赖模板或图规则，泛化能力与不确定度估计不足 ⇒ Molecular Transfo…
      │         │   │     → builds-on: Bowen Liu et al.
      │         │   │   │
 2024 │         │   │   ├── ★ Andres M. Bran et al. ✦NEW ✓   █████░░  563
      │         │   │   │   “Augmenting large language models with chemistry tools”
      │         │   │   │     通用 LLM 缺乏化学专业知识与外部工具接口，化学任务表现差 ⇒ ChemCrow：LLM+18…
      │         │   │   │     ∥ parallel: Daniil A. Boiko et al.
      │         │   │   │   │
 2025 │         │   │   │   └── ★ Tao Song et al. ✦NEW ✓   ████░░░  116
      │         │   │   │       “A Multiagent-Driven Robotic AI Chemist Enabling Autonomous Chemical Rese…”
      │         │   │   │         单一 LLM 代理难以覆盖自主化学研究全流程所需的多角色协作 ⇒ 多代理驱动的…
      │         │   │   │         → builds-on: Daniil A. Boiko et al.
      │         │   │   │
 2024 │         │   │   └── ★ Kevin Maik Jablonka et al. ✦NEW ✓   █████░░  314
      │         │   │       “Leveraging large language models for predictive chemistry”
      │         │   │         化学小数据场景需要为每个任务定制专门模型与领域知识，门槛高 ⇒ 微调 GPT-3 在…
      │         │   │         → builds-on: Derek T. Ahneman et al.
      │         │   │
 2019 │         │   └── ◉ Connor W. Coley et al. ✓   █████░░ 1082
      │         │       “A robotic platform for flow synthesis of organic compounds informed by AI planni…”
      │         │         AI 合成规划停在纸面，与真实合成执行之间存在断层 ⇒ AI 规划+机器人流动化学平台闭…
      │         │       │
 2023 │         │       └── ★ Daniil A. Boiko et al. ✦NEW ✓   █████░░  787
      │         │           “Autonomous chemical research with large language models”
      │         │             LLM 能否自主完成「设计—执行—分析」的完整科研闭环 ⇒ Coscientist：GPT-4 驱动…
      │         │             → builds-on: Derek T. Ahneman et al.
      │         │           │
 2025 │         │           └── ★ Yu Zhang et al. ✦NEW ✓   ███░░░░   25
      │         │               “Large language models to accelerate organic chemistry synthesis”
      │         │                 化学合成实践仍以费时费钱的试错流程为主，亟需先进 AI 助手 ⇒ 把 LLM 织入…
      │         │                 ∥ parallel: Tao Song et al.
      │         │
 2017 │         └── ○ Marwin Segler et al. ✓   █████░░  612
      │             “Neural-Symbolic Machine Learning for Retrosynthesis and Reaction Prediction”
      │               规则式专家系统忽略分子上下文，导致反应性冲突、模板失效 ⇒ 神经网络+符号规则的混合逆…
      │             │
 2017 │             └── ○ Bowen Liu et al. ✓   █████░░  585
      │                 “Retrosynthetic Reaction Prediction Using Neural Sequence-to-Sequence Models”
      │                   基于模板/规则的逆合成受限于模板覆盖范围与上下文冲突 ⇒ 把逆合成当作 SMILES 序列…
      │                   → builds-on: Connor W. Coley et al.
      │ 
 2010 │  ● David Rogers et al.   ███████ 7563
      │     “Extended-Connectivity Fingerprints”
      │       传统拓扑指纹为子结构/相似性搜索设计，并不适合构效关系建模 ⇒ ECFP 扩展连通性指纹，成为化学…
      │ 
 2016 │  ● Paul Raccuglia et al.   ██████░ 1703
      │     “Machine-learning-assisted materials discovery using failed experiments”
      │       实验记录本里大量「失败实验」数据从未被利用（摘要未公开，依标题/正文定位） ⇒ 用失败实验数据…
      │     │
 2018 │     └── ◉ Derek T. Ahneman et al. ✓   █████░░ 1097
      │         “Predicting reaction performance in C–N cross-coupling using machine learning”
      │           合成反应在多维化学空间中的性能（产率）难以先验预测 ⇒ 高通量实验+随机森林预测 C–N 偶联…

      ● founder  ◉ hub  ★ frontier  ·  ├── builds-on  ├┈┈ inspired-by  ∥ parallel
      citations: ✓ 17 verified  ⚠ 2 to review   (run verify.py)
```

## 发展历程

### 奠基（1995–2011）：从专家系统到机器学习

化学反应预测最早是**规则专家系统**的领地。Hiroko Satoh (1995) 的 SOPHIA 已经意识到人工编写规则的知识获取瓶颈，转而**从反应数据库自动导出知识库**——数据驱动思想的最早雏形。但真正把"学习"立起来的是 Kayala (2011)：他们把反应预测的三种途径（物理定律 / 规则系统 / 归纳学习）摆在一起，首次证明统计机器学习可以预测基元反应步，ML 反应预测路线由此开篇。表示层的基础设施也在此期间就位——Rogers (2010) 的 ECFP 指纹后来成为几乎所有化学 ML 模型的默认分子表示（对本谱系是 `inspired-by` 的支撑角色，而非主干）。

### 深度学习爆发（2016–2019）：三条路线分头突进

2016 年 Raccuglia 在 Nature 用**失败实验数据**训练模型指导水热合成、超越人类直觉，把整个化学界的目光引向数据驱动方法。此后主干在三个方向同时展开：

- **前向预测路线**：Coley (2017) 直指行业痛点——合成设计软件发展 40 年仍未普及，因为模板推荐的反应在实验室常常失败；他们用反应数据库学习给候选产物排序，确立"模板+ML"范式。Schwaller (2019) 的 Molecular Transformer 则彻底抛弃模板，把反应预测做成纯文本翻译并校准不确定度，成为此后该任务的标准基线。
- **逆合成路线**：Segler (2017) 用神经网络+符号规则的混合架构解决规则系统的"反应性冲突"；几个月后 Liu (2017) 走得更远——把逆合成直接当作 SMILES 序列到序列翻译（两者为同年递进关系，Liu 引用了 Segler）。
- **产率/条件预测路线**：Ahneman (2018, Science) 用高通量实验+随机森林预测 C–N 偶联产率，开辟了"反应性能预测"分支——这条线后来成为 LLM 时代预测化学的直接对照基线。

### 转折一：闭环（2019）——从"纸面规划"到"动手做实验"

Coley (2019, Science) 把 AI 合成规划接上**机器人流动化学平台**，首次闭环"规划→执行"。这一步改写了问题本身：此前 AI4Reaction 是预测问题，此后它逐渐变成**自主化学（autonomous chemistry）**问题——这正是四年后 LLM 代理浪潮的舞台。

### 转折二：LLM 冲击（2023–2024）

GPT-4 时代，领域再次被外部技术重塑，三个新方向几乎同时出现：

- **自主科研代理**：Boiko (2023, Nature) 的 Coscientist 证明 GPT-4 可以自主完成"设计—执行—分析"的完整科研闭环（直接续接 Coley 2019 的闭环路线与 Ahneman 2018 的反应数据）；与之**并行**，Bran (2024) 的 ChemCrow 走"LLM+18 种化学工具"的代理框架路线——两者同期互引，是典型的平行竞争工作。
- **LLM 即预测器**：Jablonka (2024) 微调 GPT-3 在分类/回归/逆设计上比肩甚至超越专用模型，把 Ahneman 一脉的"专用产率模型"逼到墙角——小数据化学任务不再必须定制模型。

### 近两年前沿（2024–2025）

- **多代理机器人化学家**：Song (2025, JACS) 在 Coscientist/ChemCrow 基础上引入多代理协作，覆盖文献调研→实验设计→执行→表征的全链路按需自主科研。
- **LLM 织入合成工作流**：Zhang (2025, Nature Machine Intelligence) 与 Song 并行，把 LLM 直接嵌进有机合成规划工作流，目标是取代"费时费钱的试错"。
- 整体趋势清晰：**单点预测 → 工具增强代理 → 多代理自主实验室**，AI4Reaction 正在与机器人化学合流。

### 开放问题

1. **数据瓶颈依旧**：高质量反应数据（尤其失败数据，Raccuglia 2016 的老问题）仍然稀缺，公开数据集偏向成功反应。
2. **可靠性与可解释**：Molecular Transformer 引入的不确定度校准（Schwaller 2019）在 LLM 代理时代尚无对应物——代理"何时不该相信自己"仍未解决。
3. **泛化到新化学空间**：产率预测模型（Ahneman 2018 一脉）在训练分布外的底物上显著退化。
4. **自主实验室的安全与边界**：Boiko (2023) 即专门讨论了自主系统被滥用合成危险品的风险，治理框架落后于能力。

## 论文清单

| Year | Paper | Cites | Role | Citation |
| ---: | --- | ---: | --- | :---: |
| 1995 | [Hiroko Satoh et al. — SOPHIA, a Knowledge Base-Guided Reaction Prediction System](https://doi.org/10.1021/ci00023a005) | 127 | founder | — |
| 2010 | [David Rogers et al. — Extended-Connectivity Fingerprints](https://doi.org/10.1021/ci100050t) | 7563 | founder | — |
| 2011 | [Matthew A. Kayala et al. — Learning to Predict Chemical Reactions](https://doi.org/10.1021/ci200207y) | 211 | other | ✓ |
| 2016 | [Paul Raccuglia et al. — Machine-learning-assisted materials discovery using failed experiments](https://doi.org/10.1038/nature17439) | 1703 | founder | — |
| 2017 | [Connor W. Coley et al. — Prediction of Organic Reaction Outcomes Using Machine Learning](https://doi.org/10.1021/acscentsci.7b00064) | 816 | other | ✓ |
| 2017 | [Marwin Segler et al. — Neural-Symbolic Machine Learning for Retrosynthesis and Reaction Prediction](https://doi.org/10.1002/chem.201605499) | 612 | other | ✓ |
| 2017 | [Bowen Liu et al. — Retrosynthetic Reaction Prediction Using Neural Sequence-to-Sequence Models](https://doi.org/10.1021/acscentsci.7b00303) | 585 | other | ✓ |
| 2018 | [Derek T. Ahneman et al. — Predicting reaction performance in C–N cross-coupling using machine learning](https://doi.org/10.1126/science.aar5169) | 1097 | hub | ✓ |
| 2019 | [Philippe Schwaller et al. — Molecular Transformer: Uncertainty-Calibrated Chemical Reaction Prediction](https://doi.org/10.1021/acscentsci.9b00576) | 852 | hub | ✓ |
| 2019 | [Connor W. Coley et al. — A robotic platform for flow synthesis of organic compounds informed by AI planning](https://doi.org/10.1126/science.aax1566) | 1082 | hub | ✓ |
| 2023 | [Daniil A. Boiko et al. — Autonomous chemical research with large language models](https://doi.org/10.1038/s41586-023-06792-0) | 787 | frontier | ✓ |
| 2024 | [Andres M. Bran et al. — Augmenting large language models with chemistry tools](https://doi.org/10.1038/s42256-024-00832-8) | 563 | frontier | ✓ |
| 2024 | [Kevin Maik Jablonka et al. — Leveraging large language models for predictive chemistry](https://doi.org/10.1038/s42256-023-00788-1) | 314 | frontier | ✓ |
| 2025 | [Tao Song et al. — A Multiagent-Driven Robotic AI Chemist Enabling Autonomous Chemical Research on Demand](https://doi.org/10.1021/jacs.4c17738) | 116 | frontier | ✓ |
| 2025 | [Yu Zhang et al. — Large language models to accelerate organic chemistry synthesis](https://doi.org/10.1038/s42256-025-01066-y) | 25 | frontier | ✓ |

---
*所有节点元数据取自 OpenAlex（2026-06），未从模型记忆引入任何论文；引用边经 `verify.py` 校验，⚠ 表示 OpenAlex 参考文献数据缺口（诚实标记，未强行声称）。*
