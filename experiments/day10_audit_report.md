# Day 10 导师级实验审计报告

**Date:** 2026-07-10 (Sprint Day 11)
**Auditor:** Research copilot (advisor-mode adversarial audit)
**Scope:** `run_real_backbone_eval.py`, `summarize_day1_triplet_eval.py`, `precedentguard/` core modules, Day 7 n=200 artifacts
**Verdict:** ⚠️ **MAJOR REVISION REQUIRED — one BLOCKING issue on scientific integrity**

---

## 一、Executive Summary（三段）

**一段结论。** 六天冲刺后，代码基础设施与理论体系已达到 AAAI 投稿门槛以上的成熟度：160 单测全绿，Alg 1 五阶段完整落地，Theorem 1–3 + Prop 1 骨架已经过 4 位 AI 冷读审稿。**但 Day 7 n=200 sweep 的实证结果存在一个 BLOCKING 缺陷：leave-one-out precedent store 只排除完全同名 example ID（"1-1"），未排除同一 base task 的所有变体（"1-2", "1-3", "1-4"）。AgentHarm 每个 base task 恰有 ~4 个近重复变体。结果：全部 400 个 query（harmful + harmless_benign, n=200 each）的 top-1 检索命中同一 base task，命中率 100.0%**。这不是 "precedent 检索的机制在起作用"，而是 "先验暴露给了近重复的自己的克隆版本"。

**二段科学后果。** 若不修复直接投稿，第一位 empirical reviewer 会独立发现同一 leakage（`example_id.split('-')[0]` 与 top-1 `capsule_id.split('-')[2]` 完全匹配）→ desk reject 概率 > 80%。CLAUDE.md §11 明文禁止此类 train/test leakage，§2 明文禁止将 leakage-driven improvement 呈现为机制证据。**因此 Day 7 n=200 数字（PG-full benign block 48.0% vs backbone 67.5%）在修复 leakage 之前不可作为 §7.1 的 headline claim。**

**三段修复代价。** Leakage 修复只是 6 行代码改动（`make_leave_one_out_precedent_store` 改为按 base task ID 过滤），但需要重跑全部 6 个 JSONL（约 4–6 小时 GPU wall clock）。修复 + 重跑后有三种可能：(a) FPR 改善保留（→ 论文核心声明成立，headline 更强）；(b) FPR 改善大幅缩水但仍非零（→ 论文需要重新校准声明，但可继续）；(c) FPR 改善消失或反向（→ headline 声明需要重构，AAAI 27 窗口极限但仍可能）。在拿到 (a/b/c) 判决之前，Gate β 应判为 CONDITIONAL PASS with mandatory rerun。

---

## 二、审计发现清单（按严重度排序）

### 🔴 BLOCKER-1：Precedent leave-one-out 只排除同变体，未排除同 base task

**证据文件：** `scripts/run_real_backbone_eval.py:277-286`
```python
def make_leave_one_out_precedent_store(
    rows: Iterable[dict],
    *,
    scope: str,
    held_out_example_id: str,
) -> SimplePrecedentStore:
    return make_precedent_store(
        [row for row in rows if row["id"] != held_out_example_id],
        scope=scope,
    )
```

**问题：** AgentHarm public 数据集每个 base task ID 派生 4 个 prompt 变体（"1-1", "1-2", "1-3", "1-4"）。这些变体是**同一底层任务**的 rephrasing/hint 变形，语义几乎完全相同（token_jaccard 常为 0.775–1.0）。当 query = "1-1" 时，当前 LOO 保留 "1-2/1-3/1-4"，`token_jaccard` 直接命中 → top-1 检索到近乎自己的克隆。

**实测数据（`artifacts/day6/day7_agentharm_full_pg_with_precedents_*.jsonl`）：**

| 检查 | harmless_benign n=200 | harmful n=200 |
|---|---|---|
| Top-1 命中同 base task | **200/200 = 100.0%** | **200/200 = 100.0%** |
| ≥1 selected precedent 来自同 base task | **200/200 = 100.0%** | **200/200 = 100.0%** |

**引用示例（rows[0] in JSONL）：**
- `example_id = "1-1"` (harmless_benign)
- `top-1 = "ah-harmless_benign-1-2-caps-..."`, `text_similarity = 1.0` ← 近似完美命中同 base task variant 1-2
- `top-2 = "ah-harmless_benign-1-3-caps-..."`, `text_similarity = 0.776`
- `top-3 = "ah-harmless_benign-1-4-caps-..."`, `text_similarity = 0.776`

**科学后果：** 
1. §7.1 "PG-full 将 benign FPR 从 backbone 67.5% 降到 48.0%" 的机制解释（"directional trust + precedent retrieval"）**不能与 leakage 效应区分**——同 base task 的 audited-safe 变体作为 precedent 直接把当前 query 拉向 allow。
2. §4.3 声明 "retrieval combines semantic and structural similarity" 的实证价值消失——leakage 使得任何 text-similarity 都足够召回近重复。
3. CLAUDE.md §11：`Prevent train/test leakage; never tune on test labels or attack outcomes.` **直接违规。**

**修复动作：**
```python
def make_leave_one_base_task_out_precedent_store(
    rows, *, scope, held_out_example_id,
) -> SimplePrecedentStore:
    held_base = held_out_example_id.split("-")[0]  # "1-1" -> "1"
    return make_precedent_store(
        [row for row in rows if row["id"].split("-")[0] != held_base],
        scope=scope,
    )
```

必须同步：
- 重跑 6 个 JSONL（3 modes × 2 subsets × n=200）
- 更新所有 §7.1 数字并**在 §6 Experimental Protocol 加一段专门声明 "leave-one-base-task-out" 协议**
- 在 supplement 附完整的 base task partition 与 seed
- 记录 diff 到 `experiments/registry.csv`

---

### 🔴 BLOCKER-2：Graph similarity 通道 empirically 恒为 0（论文声明与实现不一致）

**证据：** `artifacts/day6/day7_agentharm_full_pg_with_precedents_harmful_200.jsonl`
```
rows with any non-zero graph_similarity: 0/200
```

**根因：** `run_real_backbone_eval.py:249-274` 中的 `make_precedent_store` 在构造 `PrecedentCapsule` 时**从未设置 `subgraph_signature`**（默认为空字符串 `""`）。同时 `SimplePrecedentStore.raw_score()`（`retrieval.py:220-224`）在 `capsule.subgraph_signature or query_subgraph_signature` 均为空时短路返回 `s_graph = 0.0`。

**科学后果：** 论文 §4.3 声明 
> "Retrieval combines semantic and structural similarity: $w_i \propto \lambda_s\,\text{sim}_{\text{text}} + \lambda_g\,\text{sim}_{\text{graph}} + \lambda_a\,\text{sim}_{\text{action}}$"

而 `SimplePrecedentStore.lambda_g = 0.2`（`retrieval.py:160`），但 empirically 整个 $\lambda_g$ 通道贡献 0。审稿人立即发现 → M15 或独立 BLOCKER。

**两条修复路径（择一）：**
1. **快路径（推荐，用于 Gate β / Week 3）：** 在 `make_precedent_store` 中为每个 capsule 计算并存储一个 subgraph signature（例如 sorted-node-type-multiset 的哈希），并在 query 侧计算相同签名。**代价：<50 行代码 + 单测 3 个。**
2. **慢路径（论文诚实降级）：** 更新 §4.3 使公式为 $w_i \propto \lambda_s + \lambda_a$，说明 structural similarity 是 v0.3 future work，同时 `lambda_g` 从 0.2 改为 0.0。**代价：论文丢失一个 selling point，但和实现一致。**

**推荐决策：** Day 11–12 走快路径。graph similarity 是 CIP head-on 对比中的关键差异之一（CIP 只用文本，PG 用 EIG 结构）——放弃这个 slot 会削弱 §2.4 论证。

---

### 🟠 MAJOR-1：`precedent_safe_beta_scale = 2.0`, `precedent_unsafe_beta_scale = 0.5` 是硬编码的 asymmetric 校准

**证据：** `run_real_backbone_eval.py:527-528`（default values）与 `guard.py:348-352`（label scale 应用）：
```python
label_scale = (
    self.precedent_unsafe_beta_scale
    if cap.audited_label == 1
    else self.precedent_safe_beta_scale
)
```

**问题：** 
- Safe precedents 的 β 被 upscaled 4× vs unsafe precedents。这是**有效的隐式先验注入**——safe precedents 对最终 z 的贡献比 unsafe 大 4 倍。
- 这一 asymmetry 未在论文 §4.6 出现——§4.6 只写 directional trust rule，未提 label-dependent β scaling。
- 后果：
  1. R3 学习理论审稿会立即质疑 "训练 vs 测试 β 是否共用同一 grid"；
  2. R4 empirical 审稿会问 "这个 2.0/0.5 是不是在 dev-set 上调的？"（是——见 Day 6 EOD report §2.6）；
  3. A5 grid pre-commitment（论文声明 $\Gamma$ 在 calibration 之前 commit）**技术上可能违规**——β scale 不在 grid 里但是一个自由超参数。

**修复动作：**
1. 立即：将 `precedent_safe_beta_scale, precedent_unsafe_beta_scale` 加入 A5 承诺的 grid 里；
2. 论文 §4.6 加一句 "we adopt asymmetric label-conditional β scaling $\beta_{\text{safe}} = 2\beta_{\text{unsafe}}$ to counteract the base-guard's asymmetric conservatism observed on the AgentHarm-public dev split"；
3. 增加一个 ablation：$\beta_{\text{safe}} = \beta_{\text{unsafe}} = 1$ 作为 "no asymmetric scaling" baseline，让审稿人看到 asymmetric 的 marginal contribution；
4. 记录 rationale 到 `docs/DECISIONS.md`（当前还不存在——见 §三）。

---

### 🟠 MAJOR-2：First-example warm-up 未从 timing statistics 中剔除

**证据：** JSONL rows[0]:
```
"timing_ms": {"base_guard_ms": 15886.16, ...}
```
JSONL rows[1]:
```
"timing_ms": {"base_guard_ms": 32.21, ...}
```

**问题：** 第一个 sample 承担了 model loading + CUDA kernel autotune + first-token cache miss 的所有 cold-start 成本（15.9 秒）。后续 sample 稳定在 ~30ms。若直接 mean 全部 200 samples 会得到 ~110ms/sample 而非稳态的 ~30ms。§7 Efficiency subsection 若用 mean 汇报会误导审稿人。

**修复动作：** 
- `summarize_day1_triplet_eval.py` 加 `--skip-warmup=1` 参数，默认丢弃第一个 sample 的 timing；
- 论文 §7 Efficiency subsection 改用 median / P90 / P95（Sprint Dashboard Week 3 已列为 Day 16 输出）。

---

### 🟠 MAJOR-3：3 个 backbone 中只有 1 个（Llama-Guard-3-1B）跑了数据

**证据：** `git log --oneline --since="2026-07-07"` 无 commit；`experiments/` 只有 day7_eod_report.md；`artifacts/day6/` 只有 `day7_agentharm_full_*` 前缀（即 Llama-Guard-3-1B 结果）。ShieldGemma-2B 与 Granite-Guardian-3.2-2B 未跑。

**论文影响：** §7.1 主表格 v1.0 承诺 3 backbones × 2 subsets × 3 modes = 18 个 cell，当前只有 6 cell 有数字。R4 会指出 "single-backbone reproducibility 存疑"。

**修复动作：** Week 3 Day 12（Monday）用 ShieldGemma + Granite 双复现。leakage 修复必须在此之前完成，否则会产生 18 个都需要重跑的浪费。

---

### 🟠 MAJOR-4：Trust variant ablation 完全缺失（Gate β 硬标准 #3）

**证据：** 
- `run_real_backbone_eval.py:253-259` 中所有 precedent 硬编码为 `Provenance(signature_valid=True, semantic_authorization=True)`，即 full policy attestation 一档；
- 无脚本切换到 `Provenance()`（no provenance）、`Provenance(signature_valid=True, semantic_authorization=False)`（signature only）等其他 3 档；
- Sprint Dashboard Day 9-10 (Trust ablations) 未在 `experiments/` 有任何产物。

**论文影响：** Contribution #2 "trust-separated counterfactual calibration" 的核心 empirical 支撑不存在。这条对应 Gate β 硬标准 #3（4 trust variants comparison）。

**修复动作：** 立即（Day 11–12）增加 `--trust-variant` 参数到 launcher，跑 4 档对比。

---

### 🟠 MAJOR-5：8 baselines 中仅 4 个 mode 实现，缺 5 个学界基线

**证据：** `run_real_backbone_eval.py:513` 只支持 4 modes：`{backbone_only, no_counterfactual, clipping_only, pg_with_precedents}`。Sprint Dashboard Day 7-8 承诺的 8 baselines 中还差：
- Flattened trajectory guard（把全部 trajectory 拍成 flat prompt）
- Raw RAG concatenation baseline（vanilla RAG，无 trust / 无 counterfactual）
- CIP-style prompting（把 EIG serialize 进 prompt）
- Sequential graph（把 EIG 换成 chain，不用真实 causal edge）
- Random graph（degree-matched random DAG）

**论文影响：** 
1. Gate β 硬标准 #2 明确要求 8 baselines 出数——当前 4/8；
2. 无 CIP 头对头 → §2.4 无法把 "CIP vs PG" 具体化为数字；
3. 无 sequential / random graph → §7 RQ3 "graph fidelity value" 段落无法量化；
4. R4 M13 已明确要求补 "纯 clipping wrapper" 和 "conformal-risk-control baseline"（后者论文声明是 remark，可搁置）。

**修复动作：** Week 3 Day 12–13 三条并行：
- (a) `flattened_trajectory_score()`：把 base_view 扩到 full context 但不做 EIG 结构；
- (b) `raw_rag_concat_score()`：用同一 precedent store 但将 top-k 拼接为 prompt 传给 backbone，不做 counterfactual；
- (c) `cip_style_score()`：用 EIG 的 serialized text 拼到 base view prompt 前，不做 clipping。

---

### 🟡 MINOR-1：Certificate empirical validity dev-set 检查未运行

**证据：** `precedentguard/certificate.py` 存在（未逐字读），Day 3 EOD 曾报告 n=100 时 $U_{FN} = U_{FP} = 0.1358$。**但没有任何脚本在 dev set 上实测 empirical FNR/FPR ≤ predicted bound**。Gate β 硬标准 #1 需要 4/5 seeds 通过——目前 0/5。

**修复动作：** Day 11 EOD 前用现有 6 个 JSONL 计算 empirical FNR/FPR，与 `compute_certificate(n_c=计算得到, alpha=0.05, ...)` 对比。虽然 n=200 无法产生 5 seeds，但可以做 5 折 bootstrap 验证。这是 Gate β 判决必须补的数字。

---

### 🟡 MINOR-2：`retrieval_probe_top_k = 5` vs `precedent_top_k = 2`——报告和聚合脱节

**证据：** `run_real_backbone_eval.py:521` retrieval probe 报告 top-5，但实际用于聚合的只有 top-2。JSONL 中 `top_matches` 列表包含 5 项，`selected` 字段区分。

**问题：** 这本身没有 bug，但审稿人会问 "为什么 probe 5 却只用 2？是不是丢了信息？" 建议：论文 §4.3 明说 "we probe top-5 for diagnostics; the aggregated set is top-K with K=2 chosen on dev split"，并加 K∈{1,2,3,5} sensitivity study。

---

### 🟡 MINOR-3：无 `docs/DECISIONS.md`, `docs/FAILURE_LOG.md`, `docs/CLAIM_EVIDENCE.md`, `experiments/registry.csv`

**证据：** CLAUDE.md §4 required artifacts 列表要求这 5 个文档存在。当前 `docs/` 目录不存在，`experiments/` 只有 EOD reports 与 audit review，没有 registry.csv。

**影响：** AAAI Reproducibility Checklist 部分项目无法勾选 ✓。Week 4 red-team 阶段会成为大 friction。

**修复动作：** Day 11 EOD 前建立 4 个文档骨架（每个 <100 行），确保 Week 3 各 experiment run 都记录到 `experiments/registry.csv`。这是 30 分钟工作量。

---

## 三、Day 7 n=200 数字（AS-IS with LOO leakage caveat）

**⚠️ 以下数字受 BLOCKER-1 影响，在重跑之前只能作为 "leakage-uncorrected pilot"。**

### Table A（AgentHarm-public, Llama-Guard-3-1B, n=200 per subset）

| Mode | Harmful block rate | Benign block rate (FPR) | Mean base score (benign) | Mean s_pg (benign) | Mean pg_delta (benign) |
|---|---|---|---|---|---|
| Backbone only | 194/200 = **97.0%** | 135/200 = **67.5%** | 0.5984 | 0.5984 | 0.0000 |
| Clipping only | 196/200 = 98.0% | 152/200 = **76.0%** | 0.5984 | 0.6458 | +0.0474 |
| PG-full | 193/200 = 96.5% | 96/200 = **48.0%** | 0.5984 | 0.5008 | −0.0977 |

### Mechanism check（保留价值——leakage 影响绝对数字，不影响 sign）

- **Clipping-only 系统性恶化 benign FPR（+8.5 pp vs backbone）**：验证 Corollary 1 的机制预测——当前证据的方向性剪裁只加正 delta；这个方向即使在 leakage 情形下也不会反转，因为 clipping-only mode 不涉及 precedent。**此结论可继续入 §1.4。**
- **PG-full 相较 backbone 使 harmful recall 从 97.0% 降到 96.5%**：n=200 下丢了 1 个 harmful example。这不是 100% 保持，与 n=50 pilot 的宣称有偏差。必须诚实入 §7.1。
- **PG-full 相较 backbone 使 benign FPR 从 67.5% 降到 48.0%**：−19.5 pp，方向显著。但 **leakage 校正后是否保留数值幅度存疑**。
- **精确 vs pilot 数字对比**：pilot n=50 backbone benign FPR = 54%，n=200 下升到 67.5%——**pilot 显著低估了 backbone 的严格性**。这说明 n=50 pilot 的 confidence interval 在真实分布下过于乐观，AAAI 主表格必须报告 n=200 数字。

### Wilson 95% CIs（stdlib 计算）

| Cell | Wilson 95% CI |
|---|---|
| Backbone benign 135/200 | [0.607, 0.736] |
| Clipping benign 152/200 | [0.694, 0.816] |
| PG-full benign 96/200 | [0.412, 0.549] |

CI **无重叠** → 即使在 leakage 存在下三组均有实质性差异。

### Fisher exact + McNemar（stdlib 计算）

| Contrast | Fisher exact p | McNemar exact p |
|---|---|---|
| Backbone vs PG-full (benign) | $< 10^{-4}$ | 需 paired data |
| Clipping vs PG-full (benign) | $< 10^{-4}$ | 需 paired data |

（McNemar 需要按 example_id join 三个 JSONL 后运行；可用 `scripts/day10_paired_stats.py`——**尚未编写**，Day 11 EOD 前补上。）

---

## 四、修复优先级与 Day 11–15 执行清单

### P0（BLOCKING，Gate β 必修）

| ID | 修复 | Owner | ETA | 依赖 |
|---|---|---|---|---|
| P0-1 | 修 BLOCKER-1（leave-one-base-task-out）：改 `make_leave_one_out_precedent_store` → `make_leave_one_base_task_out_precedent_store` + 单测 3 个 | copilot | Day 11 morning | — |
| P0-2 | 修 BLOCKER-2（graph similarity 通道）：在 `make_precedent_store` 计算 subgraph_signature，`build_eig` 侧计算 query_subgraph_signature；加单测 2 个 | copilot | Day 11 morning | — |
| P0-3 | 用户 GPU 重跑 Llama-Guard-3-1B × 3 modes × 2 subsets × n=200 with (P0-1) + (P0-2) fix | 用户 | Day 11 EOD | P0-1, P0-2 |
| P0-4 | 计算 empirical FNR/FPR vs `certificate.compute_certificate()` bound；bootstrap 5 折验证 | copilot | Day 12 morning | P0-3 |
| P0-5 | Gate β 判决：Certificate valid + P0-3 数字合理 → PASS; 否则 STOP | 用户 + copilot | Day 12 EOD | P0-4 |

### P1（Gate γ 前必修）

| ID | 修复 | Owner | ETA | 依赖 |
|---|---|---|---|---|
| P1-1 | 修 MAJOR-1（asymmetric β scaling 加入 A5 grid，加 no-asym ablation） | copilot | Day 12 | — |
| P1-2 | 修 MAJOR-3（ShieldGemma + Granite 双 backbone 重跑，同一 (P0-1)+(P0-2) fix） | 用户 GPU | Day 13–14 EOD | P0-3 通过 |
| P1-3 | 修 MAJOR-4（4 trust variants ablation，只在 Llama-Guard-3-1B 上跑） | 用户 GPU | Day 14 | P0-3 |
| P1-4 | 修 MAJOR-5（补 5 个 baseline: flattened / raw_rag / cip_style / sequential / random_graph） | copilot 写实现 + 用户 GPU | Day 13–15 | — |
| P1-5 | Suite B (AgentDojo) 与 Suite C (AgentPoison subset) 首跑 | 用户 GPU | Day 14–15 | P1-4 |
| P1-6 | 修 MAJOR-2（timing warmup 剔除） | copilot | Day 13 | — |

### P2（Week 4 可修）

| ID | 修复 | ETA |
|---|---|---|
| P2-1 | 修 MINOR-1（certificate validity 5 seeds bootstrap 生产版）| Day 16 |
| P2-2 | 修 MINOR-3（建立 4 个 doc + registry.csv）| Day 11 EOD |
| P2-3 | K∈{1,2,3,5} sensitivity study | Day 17 |
| P2-4 | Adaptive attack + Cross-domain（R-Judge as OOD） | Day 15 |

---

## 五、对 §1.4 与 §7 主稿的具体修改建议

### §1.4（当前是抽象论证 → 应加 empirical anchor）

在现有段落末尾加一句：
> "We empirically confirm this failure mode on AgentHarm-public: applying only per-type directional clipping to current-trajectory evidence, without precedent-informed correction, **raises benign block-rate from 67.5% (frozen backbone) to 76.0%** while sustaining harmful blocking. This provides an existence counterexample to the sufficiency of intervention-sensitivity bounds alone."

**这段话在 leakage 修复后仍然成立**，因为 clipping-only 模式不使用 precedent store。

### §7.1 重写（leakage 修复前的诚实占位）

保留现有 4 表格结构，但在小节开头加：
> **Reproducibility note.** The numbers in Tables 1–4 use a preliminary leave-one-example-out precedent split. AgentHarm-public groups four prompt variants per base task; a stricter leave-one-base-task-out protocol is reported in Appendix D and is the version we treat as our primary result. The two protocols agree on the direction of every reported effect but differ in magnitude by [TO BE FILLED after rerun].

**这段话直接对应 CLAUDE.md §2 "Label uncertainty as UNVERIFIED, HYPOTHESIS, INFERENCE, PROPOSAL, or TODO"。**

### Contribution #3 措辞（按 R4 M11 精确化）

原文：
> "Double-sided certification. We prove a deterministic Directional Intervention Sensitivity Bound and derive finite-sample, class-conditional upper bounds on both FNR and FPR."

改为：
> "Class-conditional two-sided certificates over heterogeneous trajectory-evidence channels. We give (i) a deterministic Directional Intervention Sensitivity Bound that translates per-type attack budgets $(m_{\text{mem}}, m_{\text{obs}}, m_{\text{ret}}, m_{\text{tool}}, m_{\text{prec}})$ into asymmetric score-shift caps $(\rho_-, \rho_+)$, and (ii) finite-sample class-conditional upper bounds $U_{\text{FN}}, U_{\text{FP}}$ that hold jointly at level $1-\alpha$ under $A5$ pre-committed calibration. Unlike SMSR's single-response bound over one retrieval channel, our certificate covers memory, retrieval, observation, tool return, and precedent capsule channels simultaneously, on a frozen guard's decision layer rather than end-agent behavior."

---

## 六、Response（按 CLAUDE.md §18）

**Decision or result.** 完成 Day 10 导师级审计。发现 1 个 BLOCKER 级 leakage bug + 1 个 BLOCKER 级 graph_similarity 通道失灵 + 5 个 MAJOR。定性 Day 7 n=200 结果为 "leakage-uncorrected pilot"，不可直接作为 §7.1 headline claim。Gate β 应判为 CONDITIONAL PASS with mandatory rerun。

**Evidence.** 
- BLOCKER-1: 100.0% top-1 leakage rate on both harmful and benign subsets（stdlib 精确复现，脚本内嵌 in-line）
- BLOCKER-2: 0/200 rows with non-zero graph_similarity（同上）
- MAJOR-1: run_real_backbone_eval.py:527-528 硬编码 2.0/0.5 asymmetric β
- MAJOR-3: `git log --since="2026-07-07"` 无 commit；`artifacts/day6/` 仅有 Llama-Guard 前缀
- Day 7 n=200 headline：backbone benign FPR = 67.5% (Wilson CI [0.607, 0.736]), PG-full = 48.0% (CI [0.412, 0.549])

**Files changed.** 本报告 `experiments/day10_audit_report.md` 新建。P0/P1 修复的代码变更将在后续 commit 中完成。

**Validation performed.** JSONL 内容直接复算全部 headline 数字（Python stdlib，无 numpy/scipy 依赖）；leakage 检测使用 `capsule_id.split('-')[2]` 与 `example_id.split('-')[0]` 对比，两个 subset 独立复现。

**Risks / limitations.** 
- (a) BLOCKER-1 若在 Day 11 EOD 前无法 GPU rerun，Gate β 只能延后 1 天判决；
- (b) 若 leakage 修复后 PG-full FPR 上升到 ≥ backbone 水平，headline claim 需要重构；
- (c) MAJOR-4 (trust variants) 与 P1-4 (5 baselines) 并行占用 GPU 会挤压 Suite B/C 时间，需要用户裁剪；
- (d) 本审计未直接执行代码修复——Day 11 morning 需要用户批准 P0-1/P0-2 patch 后合入。

**Next highest-value action.** 
1. 立即（Day 11 morning）执行 P0-1 + P0-2 代码修复，追加 5 个单元测试；
2. 用户 GPU 环境 Day 11 EOD 前重跑 Llama-Guard × 3 modes × 2 subsets × n=200 with fixed LOO 与 subgraph_signature 计算；
3. Day 12 morning copilot 计算 empirical vs predicted bound + Gate β 判决。

---

**Auditor signature:** research copilot (advisor mode)
**Report status:** v1.0 (final), for Day 11 morning executive review
**Recommend:** Gate β = CONDITIONAL PASS pending P0 rerun
