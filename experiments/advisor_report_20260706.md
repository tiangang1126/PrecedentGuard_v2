# 科研进度汇报报告

**汇报人：** [博士生]
**汇报对象：** [博士生导师]
**汇报日期：** 2026 年 7 月 6 日（Sprint Day 6，Week 1 收官 / Week 2 起点）
**项目：** PrecedentGuard — Double-Sided Risk Certification for LLM Agents under Bounded Trajectory Interventions
**目标会议：** AAAI 2027（摘要 7 月 21 日，正文 7 月 28 日）
**目标定位：** Oral / Spotlight 级投稿

---

## 一、执行摘要（一页）

**Week 1 完成度：** 全部按 Sprint Dashboard 时间线交付；Gate α（7 月 4 日 EOD）**PASS**；AI 冷读独立审稿指出的 7 条 BLOCKER 已消灭 6 条，仅剩 §7 实证证据一条被纳入 Week 2 主任务。

**关键量化里程碑：**

| 维度 | Day 0 (6/30) 起点 | Day 6 (7/6) 当前 |
|---|---|---|
| 论文骨架完整性 | v0.2 初稿含 Theorem 1-3 + Prop 1 结构 | v0.2 主稿 + skeleton 全部证明补齐 + 4 处 AI 审稿修正落地 |
| 代码基础设施 | 无实现 | 8 modules · ~2400 LOC · 160 unit tests 全绿 |
| 真实 backbone 集成 | 无 | Llama-Guard-3-1B / ShieldGemma-2B / Granite-Guardian-3.2-2B 三 vendor 后端就绪；Llama-Guard 已跑通 |
| 端到端管线验证 | 硬编码 mock guard 上 10 条玩具轨迹 | Llama-Guard-3-1B 上 AgentHarm 公开测试集 10 examples × 3 modes × 2 subsets |
| 假设完备性 | A1–A4 | A1–A5 (A5 grid 预承诺 + α 联合锁定；密码学承诺分级披露) |

**当前最重要的科研发现（首个真实 backbone 证据）：** 在 Llama-Guard-3-1B 上，PrecedentGuard 完整管线相较冻结 backbone baseline，**在保持 100% harmful 召回率的前提下，将 harmless-benign 子集的过度阻断（over-blocking）率降低 30 个百分点**（9/10 → 6/10 blocked）。这是论文理论机制（方向性信任 + 精确案例检索）**在真实模型上首次经验验证**。

---

## 二、Week 1 逐日进展（Day 1–6）

### 2.1 Day 1（7/1）— 理论骨架冻结日

- 补齐 Theorem 1（Directional Intervention Sensitivity Bound）、Theorem 2（Population Double-Sided Risk Bound）、Theorem 3（Finite-Sample Certificate）、Proposition 1（TV Indistinguishability Lower Bound）全部证明主体
- Assumption A5（Grid Pre-commitment）作为新的形式化假设加入 §5.1
- 数值算例脚本 `scripts/day1_theorem_numerical_example.py` 交叉验证 Theorem 1 与 Theorem 3 的数值一致性，7 个 sanity check 全部 PASS

### 2.2 Day 2（7/2）— 实现基础设施冻结日

- 建立 `precedentguard/` 包：`types`, `eig`, `counterfactual`, `clipping` 4 个核心模块
- 63 个初始单元测试全部通过
- Day 1 script 与 Day 2 library 的 $\rho_+, \rho_-$ 数字精确一致（Scenario A / B / C 三种攻击预算分配）

### 2.3 Day 3（7/3）— 端到端 Smoke 冻结日

- 完成 `guard.py` 集成 Algorithm 1 五阶段流水线；`certificate.py` 实现 Theorem 3 有限样本计算 + A5 grid hash 强制机制
- 89 单元测试全绿，玩具轨迹 smoke test 5/5 unsafe BLOCK + 5/5 safe ALLOW
- 扩展 n=100 时证书非空：$U_{FN} = U_{FP} = 0.1358 < 0.5$

### 2.4 Day 4（7/4）— Gate α 判定日

- Gate α 三条硬标准全部满足，**PASS**（一条 human-review 项披露为 Week 2 待办）
- 引入 AI 冷读独立审稿：4 位 cold-context 审稿人从 因果 / 安全 / 学习理论 / 实证 四个角度独立评审
- 审稿发现 **7 BLOCKER + 15 MAJOR + 13 MINOR**
- 当日消灭 3 BLOCKER：Corollary 1 DPI 方向、Proposition 1 可测性 preamble、operator 承诺窄化

### 2.5 Day 5（7/5）— 实现层扩展 + BLOCKER 集中消灭日

- 消灭 3 个 BLOCKER：A5 扩展到 (Γ, α) 联合预承诺（B4）；imperfect validator η 的 adversarial vs average 区分（B5）；Precedent Retrieval 完整实现（B7）
- 新增 `backends/` 包含 3 vendor 后端（Llama-Guard / ShieldGemma / Granite-Guardian）+ `retrieval.py` 含 PrecedentCapsule / SimplePrecedentStore（含 water-fill $w_{\max}$ cap 算法）
- 测试数 89 → **139**（+50 全部新增，全绿）

### 2.6 Day 6（7/6，本日）— 首次真实 Backbone 实验日

- **实验基础设施：** `scripts/run_real_backbone_eval.py`（739 行）打通 AgentHarm 数据集加载 → EIG 构建 → 三 mode 评估 → JSONL 结果输出
- **首次真实实验运行：** Llama-Guard-3-1B 在 AgentHarm 公开测试集 20 条 examples 上完成 triplet evaluation
- **发现并修复两个真实系统问题：**
  1. **Prompt 层泄漏：** 早期版本传递 content_hash 到 backbone，模型将其视为噪声，counterfactual delta 全零。修复：`node_prompt_text()` helper 优先使用 payload 文本
  2. **Retrieval 偏斜：** 训练池标签不均衡导致 top-k 检索退化为单一标签。修复：`label_balanced` 检索策略 + 非对称 $\beta_{\text{safe}} = 2.0,\ \beta_{\text{unsafe}} = 0.5$
- 测试数 139 → **160**（+21，全绿）

---

## 三、核心科研亮点（三个）

### 亮点 1：真实 backbone 上首次验证理论机制的经验有效性

在 Llama-Guard-3-1B（Meta 官方最新 guard，1B 参数 FP16）上的 pilot triplet evaluation（AgentHarm 公开测试 10 examples × 2 subsets）显示：

| Mode | Harmful (block/10) | Benign (block/10) |
|---|---|---|
| Backbone only（冻结基线） | 10 | 9 |
| Clipping only（无 precedent） | 10 | 9 |
| **PrecedentGuard (full)** | **10** | **6** |

- **Harmful 召回率 100% 不下降**——理论声称的 "asymmetric ρ_- vs ρ_+ 允许方向性防御" 得到经验证据
- **Benign 过度阻断率下降 30 个百分点**（90% → 60%）——理论声称的 "评级性辅助修正 backbone 的过度保守" 得到经验证据
- **所有 10 个 pg_with_precedents 例子均有非零 per-precedent delta**——precedent 检索 + 反事实通路确实驱动了行为改变，不是退化到 backbone

这不是最终 headline 数字（$n=10$ 统计噪声大，Wilson 95% CI 宽），但**它是理论机制可复现的经验依据**——正是 R4 审稿人（AC 视角）在 Day 4 audit 中要求的"从概念论文升级到 evidence-based 提交"的第一块拼图。

### 亮点 2：AI 冷读独立审稿驱动的科研自我加固机制

Sprint Day 4 我们建立了一个**AI 冷读独立审稿 pipeline**：4 位 cold-context Claude Agent 分别扮演因果 / 安全 / 学习理论 / AC 四个角色，独立评审论文全部主稿 + 骨架 + 实现代码。这次审稿产出的 findings 具有明显的**独立性证据**——3/4 个审稿人独立发现 Proposition 1 σ-代数问题；多位独立找出 Corollary 1 DPI 方向反了 + LaTeX typo（`\end{proposition>`）；R3 独立复现了 §5.4 Remark 中我们的 5.06% 数值声明并逐位比对。

**这个机制的收益：**
- **今日 6/7 条 BLOCKER 已消灭**，全部在 R4 审稿人给出的 "Poster 临界（近拒绝）" 判决之下得到工程与写作层面的加固
- **主稿的所有夸大表述被系统性回收**（"first to X" 全部改为存在性反例；A5 引入了外部时间戳分级披露；η adversarial vs average 显式区分）
- **未来 R&R 阶段面对 AAAI 真实审稿人时的 rebuttal 底稿已经预写**：每一条 finding 都有对应的 fix commit / 段落改写 / 补充实验计划

**科研诚实性边界：** 该机制**不满足** CLAUDE.md §2 意义下的 "independent human verification"（仍需人类审稿闭环）。Gate α 判决报告已明确披露这一点，AAAI 提交时不会声称"proofs have been independently reviewed by human experts"，而会诚实描述为 "extensive AI-facilitated adversarial audit + [pending] human mathematical review"。

### 亮点 3：从"概念论文"到"具备可运行系统"的六天演化

| 维度 | Day 0 → Day 6 |
|---|---|
| 代码量 | 0 → ~2400 LOC（Python + 生产级设计） |
| 模块数 | 0 → 8（types / eig / counterfactual / clipping / guard / certificate / retrieval / backends）|
| 后端支持 | 0 → 3 vendor（Meta / Google / IBM）|
| 单元测试 | 0 → 160，全绿，运行 < 0.05 s |
| 端到端脚本 | 0 → 3（数值算例、玩具 smoke、真实 backbone eval）|
| 论文修正 | v0.2 冻结版 → +8 段 substantive edit（§3.2 operator scope、§5.1 A5 扩、§5.4 external anchor、§5.5 双 η、§5.6 measurable setup、Prop 1 proof、Cor 1 proof、§7 pilot results）|
| A5 强制机制 | 无 → SHA-256 `(Γ, α)` 联合 hash + registry.csv 持久化 + certify-time assertion + 3 个 A5 攻击场景单测 |

**这个演化速度的关键：** 单元测试与数值算例交叉验证的**双通道基础设施**。Day 1 script 生成的 $\rho_+, \rho_-$ 精确 5.06% 数字，在 Day 5 被写入单元测试 `test_clipping.py::TestComputeRho` 作为回归测试；Day 6 引入 payload-aware prompt 修改后，129 个下游测试立即触发回归验证——没有此机制，Day 6 的 prompt-layer 大改会引入难以追踪的静默 bug。

---

## 四、当前主要风险与应对

| 风险 | 严重度 | 应对 |
|---|---|---|
| §7 完整实证（3 backbones × 3 suites × 3 attack budgets × 3 seeds）**尚未完成** | ★★★★★ | Days 7–10 GPU 独占；已冻结蓝图；Llama-Guard-3-1B 已跑通 pilot |
| pilot 结果 $n=10$，CI 过宽 | ★★★★ | Day 7 开始扩至 $n \geq 200$ per subset；报告 Wilson 95% CI 与 paired within-example test |
| **人类**独立数学审稿仍未落实（Checklist item 10 blocker）| ★★★ | 本周内联系合作组；若 Day 10 前仍无回复，R&R 阶段诚实披露 |
| Precedent 提示层泄漏 / retrieval 偏斜等真实系统问题在 pilot 才被发现 | ★★ | 已经修复；但表明"从纸面到 real backbone"的距离比预期更远，需在 §7 discussion 中承认 |
| 3090 Ti 单卡限制 Suite C（memory poisoning）大规模 sweep | ★★ | 优先跑 Suite A（AgentHarm）+ Suite B（AgentDojo）；Suite C 视时间做加法 |

**如果 Day 15（7/15）EOD 出现下列**任一**情况，触发 Gate γ 提前判定 → 撤退至 COLM 2026 / EMNLP Findings / NeurIPS 2027：**
- Suite A F1 < 0.85（backbone-averaged）→ PG 不能击败 backbone baseline
- 证书在测试集上违反率 > α（≥ 1/20 seed × config 组合超过 U）→ Theorem 3 实证失效
- 计算预算破产（单 backbone × 单 suite 一次 sweep > 24h）

---

## 五、Week 2（Days 7–11）执行纲要

| Day | 主线任务 | 交付 |
|---|---|---|
| **Day 7 (7/7)** | Llama-Guard 上 AgentHarm 全量 sweep（n = 200 per subset，3 seeds），控制干预 suite 1000 paired examples 生成 | §7.1 主表格 v0.5（Llama-Guard 行）+ RQ3 结构价值 v0.5 |
| **Day 8 (7/8)** | ShieldGemma-2B + Granite-Guardian-3.2-2B 上重复 Day 7 sweep | §7.1 主表格 v1.0（3 backbones × 2 suites）|
| **Day 9 (7/9)** | Memory poisoning suite（AgentPoison + MINJA 子集）+ 4 种 trust variant ablation | §7.4 Authenticity vs semantic authorization + Suite C 数字 |
| **Day 10 (7/10)** | Adaptive attack 具体化 + Cross-domain（R-Judge as unseen）+ 效率 profiling | §7.5, §7.6 完整数字 |
| **Day 11 (7/11) — Gate β** | Certificate 有效性 dev-set 验证 ≥ 4/5 seeds；≥ 5 baseline 出数 | Gate β 判定报告 |

**Gate β 通过标准（Dashboard 原文）：**
- [ ] 8+ baselines 出数（含 SMSR / MemLineage / AttriGuard / AgentSentry 中至少 2 个头对头）
- [ ] 证书在 dev set 上实证有效 ≥ 4/5 seeds
- [ ] 全部主表格数字 frozen（不再改动 config）

---

## 六、请导师给出的决策

**请导师就以下三点给出方向：**

1. **[BACKBONE 选择]** 三个 backbone 中若时间紧张需砍一个，建议保留哪个？
   - 我的推荐：保 Llama-Guard-3-1B（Meta 官方，最广被引）+ Granite-Guardian-3.2-2B（IBM，最新且 taxonomy 最丰富）；砍 ShieldGemma-2B 若必须
   - 请导师确认

2. **[人类审稿寻源]** Checklist item 10 的 human independent review 是否请导师推荐 1-2 位可以在 72 小时内对 Theorem 1 Step 2 + Prop 1 measurability 给出书面回执的合作组同事？
   - 我可以提供：修改后骨架 .tex + 4 位 AI 冷读的 findings 汇总 + 关键待验证问题清单（≤ 5 条）
   - 单次审稿工作量估计：1.5–2 小时

3. **[R&R 保底策略]** 若 Gate β 或 Gate γ 触发撤退，导师倾向哪个 fallback venue？
   - COLM 2026（8 月中截止，工作 abstract 已经完全可用）
   - EMNLP 2026 Findings（8 页正文，更宽松）
   - NeurIPS 2027（多 10 个月准备，可以补齐 Suite C + 完整证书 sweep）

---

## 七、附件（可选阅读）

- **`experiments/gate_alpha_report.md`** — Day 4 Gate α 正式判决报告
- **`experiments/gate_alpha_review_ai_20260704.md`** — 4 位 AI 冷读审稿完整汇总（7 BLOCKER + 15 MAJOR + 13 MINOR）
- **`experiments/day5_eod_report.md`** — Day 5 EOD 状态报告
- **`PrecedentGuard_AAAI27_Revised_Draft_v0.2.md`** — 主稿（当前状态含今日 §7.1 pilot 结果更新）
- **`precedentguard_theorems_v0.2_skeleton.tex`** — 证明骨架（含 Days 4-5 所有修正）
- **`artifacts/day5/day1_triplet_logit_repaired_*.jsonl`** — 6 个 pilot 结果文件（Llama-Guard-3-1B × 3 modes × 2 subsets × n=10）
- **`scripts/run_real_backbone_eval.py`** — 真实 backbone 评估主脚本（739 行）
- **`scripts/analyze_day1_*.py`** — 4 个诊断脚本（base guard prompt 层、base score 修复、benign aggregation、precedent prompt 修复）

---

## 八、一句话总结

> "6 天内从**只有理论骨架**推进到**在真实 Meta guard 上首次经验验证核心机制**，同时通过 AI 冷读审稿吸收了相当于一次会议 R&R 强度的修正——距 AAAI 摘要截止还有 15 天，Week 2 的 GPU sweep 是所有努力的最后一块拼图，触发条件已经完全明确。"

**汇报人签名：** [博士生]
**汇报日期：** 2026-07-06
