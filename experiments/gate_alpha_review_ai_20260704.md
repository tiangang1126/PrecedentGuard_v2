# PrecedentGuard v0.2 — AI 冷读多角色审稿汇总

**Date:** 2026-07-04 (Sprint Day 4 EOD)
**Reviewers:** R1 (因果/语义) · R2 (安全/威胁) · R3 (学习理论) · R4 (实证/AC)
**Method:** 4 位 cold-context `general-purpose` Agent 并行独立评审；每位只读指定 4 份文件（无对话历史、无 CLAUDE.md、无 sprint dashboard）
**Manuscript scope:** `PrecedentGuard_AAAI27_Revised_Draft_v0.2.md` + `precedentguard_theorems_v0.2_skeleton.tex` + 6 个实现模块 + smoke log

---

## 边界声明（CLAUDE.md §2 合规）

本报告是 **AI 冷读对抗性审稿**，不满足 CLAUDE.md §2 意义下的"independent human verification"。骨架 §7 Checklist item 10 状态维持 **`[BLOCKER: 人类审稿延后到 Day 5-7]`**，本次不修改。R&R 阶段若被问及审稿情况，诚实答复"AI 冷读审稿多轮 + 人类审稿仍待落实"。

---

## 一、共识判定

| Reviewer | Verdict | Top 关注 |
|---|---|---|
| R1 因果/语义 | **MAJOR REVISION** | 论文承诺 4 种 operator（ABL/REPL/REPLAY/WITHHOLD）但实现只有 2 种 |
| R2 安全/威胁 | **MAJOR REVISION** | A4 排除 policy-attested compromise 后再用 §5.5 η 补丁——两个量非可交换；A5 SHA-256 只是 self-attestation |
| R3 学习理论 | **MINOR REVISION** | Thm 1 Step 4′ 单调性论证需改为凸/包容形式；Thm 2 需显式覆盖 randomized guard |
| R4 实证/AC | **Poster（临界 Reject）** | §7 全章占位；无实证结果；`base=0.700/0.150` 硬编码 mock 不构成 reproducibility 证据 |

**综合判定：MAJOR REVISION。** 如果不能在 7/18 之前拿到真实端到端数字，**应放弃 AAAI-27 投稿窗口，改投 COLM 2026 / EMNLP 2026 Findings 或 NeurIPS 2027**。

---

## 二、BLOCKER 汇总（7 条，其中 3 条被多位审稿人独立捕获）

### B1. **[R1, R2, R4]** Corollary 1 证明 + LaTeX 语法 + 语义过度依赖

**R1 (数学):** Corollary 1 proof 中 DPI 方向搞反——正确陈述是 $\TV(Q_1^O, Q_0^O) \le \TV(Q_1^{O,Z}, Q_0^{O,Z})$（marginalization 缩小 TV），但结论方向"添加 Z 不减少 TV"仍成立；需要显式写"$\pi: (O,Z) \to O$ 是投影 channel"这一步。

**R2 (语义):** §1.2 / §8.2 把 Corollary 1 用作"signatures alone are weaker"的正当性依据——但 Corollary 1 只是**必要条件**（存在无信息签名），非**充分条件**。

**R4 (LaTeX 编译):** Skeleton L436 `\end{proposition>` 是 typo（多位审稿人独立捕获），会导致 `pdflatex` 编译失败。**这条也是骨架当前状态的可执行性 BLOCKER。**

**修复：** ①改 DPI 方向陈述；②Corollary 1 定位改为"存在性反例"；③修 typo。

### B2. **[R1]** 论文承诺 4 种 intervention operator，实现只支持 2 种

`counterfactual_delta` 明确 `raise ValueError` on REPLAY / WITHHOLDING（L219-222）。但 §3.2 / §4.4 全篇将四者平列，Contribution #1 也承诺"支持 controlled node ablation and replacement"（用词已窄化，但 §3.2 定义域完整）。

**修复：** 三选一——(a) 实现 REPLAY/WITHHOLDING；(b) 主稿明说"only ABL/REPL are implemented; REPLAY/WITHHOLDING are declared for extensibility, all theorems depend only on the former"；(c) 移入 future work。**推荐 (b)**——最快、诚实、不损失叙事。

### B3. **[R1, R2, R3]** Proposition 1 measurable setup 未形式化

**R1:** attacker kernel $a: \mathcal{X} \to \mathcal{X}$ 与 $Y$ 联合可测性未声明——需明确 label-aware vs label-oblivious 假设。$Q_y$ 定义"pushforward on $\sigma(O)$"记号滑动（$\sigma(O)$ 是 $\Omega$ 子代数，$Q_y$ 是 $\mathcal{Y}$ 上的 Borel 测度）。

**R2:** validator TCB 的 adversarial robustness 未形式化。

**R3:** Prop 1 proof "inf attained by NP test" 需明说"允许 randomized decision rules"。

**修复：** Prop 1 前补一段 measurability preamble：
```
Let (Ω, F, Pr) carry (X, Y, U_adv). Attacker a: X × U → X is measurable.
Label-aware or label-oblivious assumption: [choose one, declare explicitly].
Q_y(B) := Pr(O(a(X)) ∈ B | Y = y)  is a probability measure on (Y, Borel(Y)).
h: Y → {0,1} is Borel-measurable; h ∘ O is σ(O)-measurable on Ω.
Randomized decision rules are permitted; NP inf is attained by NP randomized test (Tsybakov 2009 Thm 2.2).
```

### B4. **[R2, R3]** Assumption A5 只封锁 Γ，未封锁 α；registry.csv 不是密码学承诺

**R2:** SHA-256 + local CSV 只是 **self-attestation**——insider 可以在 calibration 后重写 CSV，篡改时间戳。匿名审稿人无法验证。

**R3:** `hoeffding_tail(..., alpha=...)` 允许运行时任意传入 α；α 网格若被后验选择，会产生 selective inference 陷阱。

**修复：** ①A5 扩为"$(Γ, α)$ 均在 calibration 前 commit"；②`commit_grid_hash` 一并 hash α；③论文明说 "external timestamp anchor (RFC 3161 / OpenTimestamps / public git tag) is required for adversarial-verifiable pre-commitment; current implementation is honest-author baseline"。

### B5. **[R2]** A4 vs §5.5 η 补丁——非可交换量

A4 声明"attacker 不能伪造 attestation"；§5.5 用 $U_{\text{FN}}^\eta \le U_{\text{FN}} + \eta$ 处理 validator 错误。但 A4 是**任意攻击下**的排除，$\eta$ 是**部署平均错误率**——**adversarial worst-case $\eta_{\text{adv}}$ 可以远高于 deployment-average $\eta$**。

**修复：** ①明确 $\eta$ 的类型（deployment-average vs adversarial worst-case）；②若报告的是 average，加 note 说明 adversarial extension is future work；③或者把 validator 加进 Prop 1 的观测通道 $O$，从 TV 界重新推导。

### B6. **[R4]** §7 全章占位，无真实实证

**当前状态：** `experiments/day3_smoke.log` 中 `base=0.700/0.150` 是硬编码 mock，10 条轨迹是 wiring test。§7 全部 `[RESULT TO BE INSERTED]`。

**修复（时间关键）：** 
- 7/6 前：冻结 Suite = {AgentHarm 200×2, AgentDojo full, AgentPoison memory subset}
- 7/12 前：≥3 backbones × 3 suites × 3 attack budgets × 5 seeds → §7.1 主表格
- 7/18 前：controlled intervention suite（1000 paired，**全部合成生成**，公开生成脚本+种子）
- **如果 7/18 前无法达成：STOP，转 COLM/EMNLP/NeurIPS。**

### B7. **[R4]** guard.py 完全没有 precedent retrieval

论文标题即 "PrecedentGuard"，Abstract 强调 "precedent capsule"，§4.3 半页描述 capsule schema——**当前代码没有 precedent 任何一行**。

**修复：** ①7/11 前实现 precedent 检索 + capsule scoring；②或降低 v0.3 标题/摘要中 precedent 的地位为"future extension"（但代价：论文改名或大幅重写）。

---

## 三、MAJOR 汇总（按类别）

### 理论层（Thm 1-3 + Prop 1）

**M1 [R1]** §4.4 q>1 方差归约与确定性 guard 自相矛盾——`counterfactual_delta` 无 seed 入参，stochastic backbone 下无法保持 paired variance。**修复：** 加 `seeds: Sequence[int] | None` 参数；§4.4 明说 q>1 仅在 stochastic backbone 下有意义。

**M2 [R3]** Thm 1 Step 4′ 单调性论证需重写为**凸/端点**形式（$r_-$ 是 $m_k^{ins,unattested}$ 的线性函数 → 极值在端点 → 端点即 $m_k^{ins,unattested}=0$）。

**M3 [R3]** Thm 2 未显式覆盖 randomized guard；边界 $M_1 = \rho_-$ 严格属于"通过"而非"假阴"。**修复：** 加一句 randomized extension；边界处理明说"$\le$ 是保守选择"。

**M4 [R3]** i.i.d. 假设应升为 **A6**（明确声明类条件 i.i.d.，若样本为轨迹步骤则改用 clustered Hoeffding）。

**M5 [R1]** Prop 1 proof "max(a,b) ≥ (a+b)/2 for non-negative a,b" 的非负条件多余（对任意实数成立）。改为"for any a, b"。

### 安全层（威胁模型 + 信任）

**M6 [R2]** vector budget $\mathbf m$ 缺失维度：cross-session coordination、query budget、adaptivity flag。**修复：** §3.3 扩为 $(\mathbf m, Q, T, b)$；说明 ρ_+/ρ_- 对新维度的单调性。

**M7 [R2]** §3.3 "intent I is conditioned on" **隐式排除 intent-hijacking**——审稿人会把这读作避战。**修复：** 显式列为 out-of-scope，或加入 intent-integrity channel。

**M8 [R2]** §4.6 refined ρ_- 依赖"防御方能观察/强制 $m_k^{ins,unattested}$"——但实际部署中防御方看不到攻击者预算组成。**修复：** 把 $m_k^{ins,unattested}$ 改写为 "defender-enforced ceiling on unauthenticated insertions"，并说明运行时如何强制该上限。

**M9 [R2]** `Provenance.is_attested` 缺 replay / revocation / nonce 保护。**修复：** 或补 3 条件，或明确排除。

**M10 [R2]** §8.2 vs SMSR 对齐过度：措辞 (1)(4)(5) 需软化；vs MemLineage 需承认 "structural lineage vs semantic attestation" 是不同 trust root。

### 实证层（§6-§7 + 实现）

**M11 [R4]** §1.5 Contribution #3 "Double-sided certification" **过度声明**——SMSR 也是 certified defense。**修复：** 改为 "class-conditional two-sided extension of SMSR's single-response bound, over heterogeneous trajectory-evidence channels, on a frozen guard's decision layer rather than end-agent behavior"。

**M12 [R4]** §6.6 Attack 6 (adaptive) 过于抽象——无优化算法、无预算。**修复：** 明说 "coordinate ascent over per-type caps, budget=100 queries/trajectory, warm-started from unsigned insertion attack"。

**M13 [R4]** 缺失关键 baseline：(a) **SMSR 头对头**（在 SMSR 自己的 setting 上跑 PG）；(b) **纯 clipping wrapper（无 counterfactual）**——隔离 counterfactual 贡献；(c) **conformal-risk-control baseline**（否则审稿人问"为什么不用更好的工具"）。

**M14 [R4]** §6.8 ablation chain 中 step 4↔step 5 在 `aggregate()` 里耦合——无法真正隔离 counterfactual decomposition vs clipping 各自贡献。**修复：** 提供 4-only 和 5-only 独立 config。

**M15 [R2]** SMSR 的 impossibility（provenance-free retrieval-time filter）与 PG 的 Prop 1（TV lower bound）**是正交结论**，但主稿 §2.3 / §8.2 表述模糊，容易被读作 "PG subsumes SMSR"。**修复：** §2.3 加一句"两者正交：SMSR 说'缺 provenance 不可 certify'，Prop 1 说'仅有 authenticity 不能提升下界'"。

### 一致性层（论文 ↔ 实现）

**M16 [R1, R4]** 论文 vs 实现的三处不一致：
- REPLAY / WITHHOLDING operator 未实现（B2 已列）
- q>1 无 seed 控制（M1 已列）
- precedent retrieval 完全缺失（B7 已列）
- `EIG.add_edge` 不校验 edge type 语义合法性——A1 是纯人工承诺

---

## 四、MINOR + NITPICK（批量整理）

| # | Reviewer | 位置 | 内容 | 快速修复 |
|---|---|---|---|---|
| N1 | R1 | Skeleton L361 | Thm 3 union bound 用 n_min 但代入用 n_c | 一句 Remark 澄清 |
| N2 | R2 | §6.6 | attacker 是否已知 calibration data 未说明 | 一句声明 |
| N3 | R2 | types.py | `Provenance.expiry_epoch_ms` 用 `current_epoch_ms` 判定；来源需在 TCB 内 | 加 docstring |
| N4 | R2 | types.py | TOOL_ARG / DERIVED_SUMMARY 非 mutable 但下游可变 | §3.3 澄清"mutable = 直接受 attacker control" |
| N5 | R3 | certificate.py | `hoeffding_tail` 不校验 α 属于 registry | commit_grid_hash 一并 hash α |
| N6 | R3 | certificate.py | `CertificateConfig` 含 `Mapping` 但 frozen=True 不保证 hashability | 重载 __hash__ 或用 serialize() 比较 |
| N7 | R3 | clipping.py | `compute_rho` 未校验 `m.keys() ⊆ caps_by_type.keys()` | 加断言 |
| N8 | R4 | §5.4 Remark | 半页篇幅——超出主论文比重 | 移到 appendix |
| N9 | R4 | §6.7 | "certificate violation frequency" 定义模糊 | 明确 = empirical FNR > U_FN 的比例 |
| N10 | R4 | §6.10 | 无 table skeleton | 补 Table 1-3 骨架 |
| N11 | R4 | §8-9 | Failure modes vs Limitations 未映射 | §9 扩为 6 条对齐 §8.5 |
| N12 | R1,R2,R3,R4 | Skeleton L436 | `\end{proposition>` typo（LaTeX 编译错误） | 已列为 B1 |
| N13 | R4 | §4 全篇 | "training-free" 与 β_e dev-set tuning 矛盾 | 改为"no gradient-based fine-tuning; only hyperparameter calibration" |

---

## 五、7 天补救计划（Day 5-11，Gate β 前）

**优先级 P0（必做，无这些 Gate β 必败）：**

| Day | 任务 | 对应 BLOCKER/MAJOR |
|---|---|---|
| 7/5 (Day 5) | 修 B1 三处（DPI 方向 + Corollary 1 定位 + LaTeX typo）→ 骨架编译通过 | B1 |
| 7/5 (Day 5) | 修 B2（主稿明说 REPL/ABL only；REPLAY/WITHHOLD 归 future）| B2 |
| 7/5 (Day 5) | 修 B3（Prop 1 measurability preamble）| B3, M5 |
| 7/6 (Day 6) | 修 B4（A5 扩为 (Γ,α)-预承诺；`certificate.py` commit_grid_hash 加 α；论文明说 external timestamp is required for adversarial-verifiable claim）| B4 |
| 7/6 (Day 6) | **Suite 冻结** = {AgentHarm 200×2, AgentDojo full, AgentPoison subset} | B6 |
| 7/7-8 (Day 7-8) | 3 backbones × 3 suites × 3 budgets × 5 seeds → §7.1 主表格 | B6 |
| 7/9 (Day 9) | 修 M2 (Thm 1 Step 4′ 凸/端点论证) + M3 (Thm 2 randomized + 边界) + M4 (A6 i.i.d.) | M2/M3/M4 |
| 7/9-10 (Day 9-10) | 修 B7（实现 precedent 检索），或全篇改标题/摘要 | B7 |
| 7/11 (Day 11) | Trust ablations + Certificate empirical validity ≥4/5 seeds pass | Gate β 判定 |

**优先级 P1（Should，Gate γ 前）：**
- 修 M1 (q>1 seed 参数)
- 修 M6-M9 (威胁模型扩展)
- 修 M10 (SMSR/MemLineage 对齐)
- 修 M11 (Contribution #3 措辞)
- 修 M12-M14 (Adaptive attack 具体化 + baseline 补齐 + ablation 解耦)

**优先级 P2（Nice-to-have，7/18 前）：**
- N1-N13 全部修

---

## 六、Gate α 判定更新

**原判定（2026-07-04 早）：Gate α = PASS with deferral on Checklist item 10 (human review)**

**AI 冷读审稿后修订（2026-07-04 EOD）：**

| Gate α 标准 | 原判定 | 修订判定 |
|---|---|---|
| 4 proofs complete and reviewed | ✅ PASS | ✅ **PASS**（AI 冷读 x2 完成，但 BLOCKER B1-B4 需要 Day 5 补齐；不影响 Gate α 已通过，但 Gate β 前必须解决） |
| Min impl runs on toy trajectories | ✅ PASS | ⚠️ **PASS with caveat**——smoke log 硬编码 mock，不构成 reproducibility 证据；需要 Day 5-8 换真实 backbone |
| Related Work updated for v0.2 | ✅ PASS | ⚠️ **PASS with caveat**——SMSR/MemLineage 对齐需软化，Contribution #3 措辞需精确化（Day 5-6 修） |

**结论：** Gate α 判定 **维持 PASS**，但**新增 4 条 BLOCKER (B1-B4) 与 15 条 MAJOR** 进入 Day 5-11 补救计划。**Sprint 继续，不触发 STOP-LOSS。**

**新的关键判断：** 如果 B6 (§7 实证) 在 **7/18 EOD** 前无法交付 3-backbone × 3-suite 的真实数字，**触发 Gate γ 提前判定**，改投目标从 AAAI-27 降为：
- **A 计划**：AAAI-27 Poster 提交（实证不足但理论清晰）
- **B 计划**：COLM 2026 或 EMNLP 2026 Findings（8 页更适合当前状态）
- **C 计划**：NeurIPS 2027（8 月截止，多 5 周准备时间）

---

## 七、审稿人 Attack Log 摘要（用于 rebuttal 准备）

**已确认 SURVIVED 的攻击（可以在 R&R 里正面回应）：**
- R1 F2: paper discipline about δ_e ≠ ATE 保持得很好
- R2 F5: Prop 1 与 SMSR impossibility 是正交结论（非蕴含）
- R3 F3: Hoeffding + union bound 记账正确
- R3 F6: 数值声明 5.06% 与范围 (2.97%, 7.26%) 独立复现精确匹配
- R3 F7: `compute_rho` 与 Thm 1 statement 完全一致

**已 BROKEN 的攻击（必须在 Day 5-11 补上防御）：**
- R1 F5: 论文声称 4 operator 实现 2 个 → B2
- R2 F1: cross-session poisoning → M6
- R2 F2: adversarial-worst-case η → B5
- R2 F3: A5 insider 篡改 → B4
- R2 F4: unauth deletion 未被独立预算 → M8
- R4 全部（§7 空洞、缺 baseline、Contribution #3 overclaim）→ B6, B7, M11-M14

---

## 八、审稿产物索引

**冷读 Agent IDs（用于后续 SendMessage 追问）：**
- R1: `a3db96700cbc4e652`
- R2: `a558819479263ef4c`
- R3: `a68613e3d778c5289`
- R4: `a0b1e932d40d820c6`

（这些 ID 只在当前 Claude session 有效，session 结束即失效。若需保留原始 raw review 输出，请把 4 个 review 完整文本另存 markdown。）

---

**Signed:** AI research-copilot (adversarial audit mode)
**Sprint:** AAAI 2027 (Abstract 7/21, Paper 7/28)
**Next stop-loss:** Gate β (7/11 EOD) — 5+ baselines implemented + certificate empirically valid on dev set
**Human independent review status:** Still deferred (Checklist item 10)
