# Week 3 优化执行路线（Day 11–15）

**Date:** 2026-07-11
**Sprint status:** Week 2 收尾 → Week 3 起点
**Anchor documents:** `experiments/day10_audit_report.md`, `Sprint_Dashboard_4Week_AAAI27.md`, `PrecedentGuard_AAAI27_Revised_Draft_v0.2.md`
**Compute budget:** RTX 3090 Ti FP16 主机 + 备用 4×H100 只用于 Week 4 全量重跑

---

## 一、Week 3 目标：从 "leakage-uncorrected pilot" 升级为 "AAAI Oral-defensible 主结果"

Week 3 是从 "机制上可讲通" 到 "实证上抗审稿" 的决定性一周。Day 15 EOD 前必须交付：

1. **LOBTO 主结果**（3 backbones × 3 modes × 2 subsets × n=200 或以上）
2. **证书 empirical validity** dev-set 上 4/5 seeds 通过
3. **Trust variant ablation** 4 档全出数
4. **5+ baselines** 出数（含 CIP-style 头对头）
5. **Suite B (AgentDojo) 或 Suite C (AgentPoison subset) 首跑**

如果任一子目标 Day 15 EOD 前未完成，**触发 Gate γ 提前判决**，直接进入撤退分支（COLM 2026 / EMNLP 2026 Findings / NeurIPS 2027）。

---

## 二、每日执行清单

### Day 11 (2026-07-11, Sat) — P0 代码修复 + LOBTO 首轮小样验证

| 时段 | 任务 | 交付 | Owner |
|---|---|---|---|
| 09:00–10:00 | 复核 `experiments/day10_audit_report.md` 全部结论；用户确认 leakage 判决 | 确认签字 | 用户 |
| 10:00–11:00 | 用户在 GPU 环境用**修复后**的 `run_real_backbone_eval.py`（含 LOBTO + subgraph_signature + `--trust-variant`）小样跑 n=30 verify | 3 个 JSONL：`day11_verify_{mode}_harmless_benign_30.jsonl` | 用户 |
| 11:00–12:00 | 复现 §7.1.d clipping-only 数字（应该完全不变，因为不涉及 store） | 数值一致性确认 | copilot |
| 14:00–17:00 | 用户跑 LOBTO n=200 sweep（Llama-Guard-3-1B × 3 modes × 2 subsets = 6 JSONL）| 6 个 JSONL 落在 `artifacts/day11/` | 用户 |
| 17:00–19:00 | copilot 分析 LOBTO n=200 数字、更新 §7.1.b 主结果表、判决 mechanism 是否 survive leakage 修复 | §7.1.b 表填数；Day 11 EOD 报告 | copilot |

**Day 11 EOD 判决点：**
- 若 LOBTO n=200 下 PG-full benign FPR $< 0.675$ 且 harmful recall $\ge 0.94$ → **mechanism survived leakage fix，进入 Day 12**
- 若 LOBTO n=200 下 PG-full benign FPR $\ge 0.675$ → **触发 Gate γ 提前判决**，评估撤退

### Day 12 (2026-07-12, Sun) — Gate β 判决 + 证书 empirical 有效性 + β sensitivity

| 时段 | 任务 | 交付 | Owner |
|---|---|---|---|
| 09:00–10:30 | copilot 写 `scripts/day12_certificate_empirical_validity.py`——从 LOBTO JSONL 计算 empirical FNR/FPR，与 `precedentguard.certificate.compute_certificate()` 预测的 $U_{FN}, U_{FP}$ 对比，5 折 bootstrap seed | script + CSV 表 | copilot |
| 10:30–12:00 | 判决 Gate β：empirical FNR/FPR ≤ 预测 bound 在 ≥4/5 seeds 上；文档化到 `experiments/gate_beta_report.md` | Gate β verdict 报告 | copilot |
| 14:00–17:00 | 用户跑 asymmetric β ablation：`--precedent-safe-beta-scale 1.0 --precedent-unsafe-beta-scale 1.0`（对照）vs 2.0/0.5（v0.2 默认）；n=200 | 3 个额外 JSONL；`experiments/day12_beta_ablation_report.md` | 用户 GPU + copilot |
| 17:00–19:00 | 更新 §7.1.b 加入 β ablation 表格；将 β scale grid 显式承诺到 A5 grid | 主稿 §7.1.b + §4.6 修订 | copilot |

**Day 12 EOD 判决点：**
- Gate β：4/5 seeds 有效 → PASS，进入 Day 13
- Gate β：≤3/5 seeds → 撤退到 NeurIPS 2027

### Day 13 (2026-07-13, Mon) — 补 5 个 baseline + ShieldGemma 双复现

| 时段 | 任务 | 交付 | Owner |
|---|---|---|---|
| 09:00–12:00 | copilot 实现 4 个新 mode: `flattened_trajectory`, `raw_rag_concat`, `cip_style`, `sequential_graph` | 4 个新 mode + 6 个新单元测试 | copilot |
| 14:00–17:00 | 用户跑 ShieldGemma-2B × 6 modes × 2 subsets × n=200（12 个 JSONL）+ Llama-Guard × 4 个新 mode × 2 subsets（8 个 JSONL）| 20 个 JSONL | 用户 GPU |
| 17:00–19:00 | copilot 合并所有数字到 §7.1.b 主表格；Fisher/McNemar 全对比 | §7.1 主表格 v2.0（3 backbones × 8 modes 部分填充）| copilot |

**Day 13 EOD 目标：** 主表格 8 baselines × 2 backbones × 2 subsets 出数。

### Day 14 (2026-07-14, Tue) — Granite 三 backbone 复现 + Trust variant ablation

| 时段 | 任务 | 交付 | Owner |
|---|---|---|---|
| 09:00–12:00 | 用户跑 Granite-Guardian-3.2-2B × 8 modes × 2 subsets × n=200（16 个 JSONL） | 16 个 JSONL | 用户 GPU |
| 14:00–17:00 | 用户跑 Llama-Guard × PG-full × 4 trust variants × 2 subsets × n=200（`--trust-variant`：no_provenance / signature_only / lineage / policy_attested，共 8 个 JSONL） | 8 个 JSONL | 用户 GPU |
| 17:00–19:00 | copilot 写 §7.4 authenticity vs semantic authorization 段落；填数据；Fisher 三配对 | §7.4 完整 draft | copilot |

**Day 14 EOD 目标：** 3-backbone × 8-mode 主表格填满；trust variant 表格出数。

### Day 15 (2026-07-15, Wed) — Suite B/C 首跑 + Gate γ 判决

| 时段 | 任务 | 交付 | Owner |
|---|---|---|---|
| 09:00–12:00 | copilot 写 AgentDojo 数据加载器（复用现有 `run_real_backbone_eval.py`；改 `resolve_dataset_file` 支持 AgentDojo 格式） | `scripts/agentdojo_loader.py` + 单测 | copilot |
| 14:00–19:00 | 用户跑 Llama-Guard-3-1B × PG-full + backbone_only × AgentDojo 全测试集 | 2 个 AgentDojo JSONL | 用户 GPU |
| 19:00–21:00 | Gate γ 判决：Suite A 完成 ✓；Suite B 出数 ✓；表格/图冻结候选决定 | `experiments/gate_gamma_report.md` | copilot |

**Day 15 EOD 判决点：**
- Gate γ PASS → 进入 Week 4 写作 + red-team review
- Gate γ FAIL → 裁减 Suite C（AgentPoison subset），改投 ICLR 2028

---

## 三、脚本级具体优化（copilot Day 12–13 交付）

### 3.1 `scripts/day12_certificate_empirical_validity.py`（新建）

```python
"""
Certificate empirical validity check (Gate β #1).

For each JSONL in --root matching --prefix:
  1. compute empirical FNR = (harmful allow count) / (harmful total)
  2. compute empirical FPR = (benign block count) / (benign total)
  3. call compute_certificate(n_c=len(calibration_split), alpha=0.05, ...)
     to get predicted U_FN, U_FP
  4. bootstrap 5 folds: 80% calibration / 20% test split, repeat with seeds
     [7, 13, 17, 19, 23]; check U_FN >= empirical_FNR AND U_FP >= empirical_FPR
     on the test split.
  5. emit CSV with columns:
     seed, split_size, empirical_FNR, U_FN, empirical_FPR, U_FP,
     FNR_ok (bool), FPR_ok (bool), both_ok (bool)
  6. report "K/5 seeds valid" for Gate β verdict.

Usage:
  python scripts/day12_certificate_empirical_validity.py \
    --root artifacts/day11 \
    --prefix day11_lobto_llama_guard \
    --alpha 0.05 \
    --output experiments/day12_certificate_validity.csv
"""
```

**核心逻辑：** 从 JSONL 直接 join by `example_id`，用 stdlib 计算，无 numpy/scipy 依赖，确保与 `precedentguard.certificate` 的接口一致。这个脚本是 Gate β 判决的定量证据。

### 3.2 补 4 个新 baseline mode（`run_real_backbone_eval.py` 扩展）

| Mode 名 | 语义 | 实现要点 |
|---|---|---|
| `flattened_trajectory` | 把 trajectory 全部拍成 flat prompt 传给 backbone，不用 EIG | 拼接 payload；不做 counterfactual；一次 backbone 调用 |
| `raw_rag_concat` | 用同一 precedent store retrieve top-k，把 capsule 文本拼到 prompt 后，不做 counterfactual、不做 clipping、不做 directional trust | 一次 backbone 调用；对比 vanilla RAG |
| `cip_style` | 把 EIG 结构 serialize 到 prompt 中作为 causal-influence hint（复现 CIP 的 prompt-engineering 用法） | 一次 backbone 调用；文本形式的 "node -> node" 序列化 |
| `sequential_graph` | 用 chain graph 替代 EIG（每个 node 只连前一个），保留其他所有 PG-full 流程 | 修改 `build_eig` 分支；测同一 counterfactual |
| `random_graph` | degree-matched random DAG 替代 EIG | 同上；seed 控制以保证复现 |

**测试预算：** 每个 mode 加 3 个单测（determinism / empty trajectory / retrieval integration）。

### 3.3 `scripts/day12_beta_ablation.sh`（新建）

按照 A5 grid pre-commitment 的原则，在 registry.csv 中先 commit β scale grid，然后跑 `--precedent-safe-beta-scale ∈ {1.0, 1.5, 2.0, 3.0}` × `--precedent-unsafe-beta-scale ∈ {0.33, 0.5, 0.75, 1.0}` 的 4×4 grid。用户执行前必须先跑 `commit_grid_hash` 单测 assert grid hash 已入库。

**这个 ablation 直接回应 R4 M11 和 Day 10 audit MAJOR-1。**

---

## 四、论文侧同步优化（copilot Day 11–15 增量提交）

按 Day 10 audit §五给出的 §1.4 / §7.1 修订路线，Week 3 每日 EOD 递交主稿差异到 git。当前状态：

- ✅ §1.4 empirical anchor（Day 10 audit 完成）
- ✅ Contribution #3 措辞（Day 10 audit 完成）
- ✅ §7.1.a LOEO n=200 数字入档（Day 10 audit 完成）
- ✅ §7.1.b LOBTO protocol 声明（Day 10 audit 完成，数字待 Day 11 填）
- ✅ §7.1.d clipping-only 反证段落（Day 10 audit 完成）
- ⏳ §7.2 Certificate validity（Day 12 EOD 填数字）
- ⏳ §7.3 Graph fidelity vs sequential/random（Day 13 EOD 填数字）
- ⏳ §7.4 Trust variants（Day 14 EOD 填数字）
- ⏳ §7.5 Adaptive + Cross-domain（Day 15 EOD 或延后）
- ⏳ §7.6 Efficiency（Day 16 EOD）
- ⏳ Abstract 重写（Day 15 EOD，基于 §7 全表冻结）
- ⏳ §8 Discussion 结合 §7 数字（Day 16）
- ⏳ §9 Limitations 明确列出 leakage 修复历史（Day 16）

---

## 五、Week 3 关键风险与应对

| 风险 | 概率 | 严重度 | 应对 |
|---|---|---|---|
| LOBTO 下 PG-full FPR 上升到 backbone 水平 → mechanism 声明失效 | 30% | ★★★★★ | 立即触发 Gate γ；不硬撑；改投 NeurIPS 2027 或降级为 methodology-only 短文 |
| 证书 empirical 在 dev-set 上大面积 violate | 20% | ★★★★★ | 检查 α / grid pre-commitment 是否正确；若确实 violate → 论文必须显式披露，用 conformal risk control 替代 |
| ShieldGemma / Granite 上 PG-full 效应远弱于 Llama-Guard | 40% | ★★★ | 主表格诚实报告；论文声明 "backbone-specific effect"，不冒充 "backbone-agnostic" |
| Suite B (AgentDojo) 数据加载器写不完 | 40% | ★★★ | Day 15 morning 决定：如果加载器有 bug → 转 Suite C AgentPoison subset；两个 suite 只需要 1 个出数 |
| 4 新 baseline mode 引入回归 bug | 30% | ★★ | 每个 mode 3 个单测；main sweep 前必须 165 → 180+ tests green |
| 用户 GPU 长时间跑 sweep 中断（网络、内存 OOM） | 30% | ★★★ | JSONL 是 append-only，中断可继续；Day 12 加 `--resume` flag 支持 |
| β ablation 在某些 config 下 FPR 反向恶化 | 40% | ★★ | 这本身是 valid finding；报告 4×4 grid 里的 (safe_β, unsafe_β) 最优；A5 grid pre-commitment 保护免受 post-hoc selection |
| 主稿 §7 内容超页数（AAAI 7 页硬约束） | 60% | ★★★ | Suite A + Trust variants + Efficiency 放主文；Suite B/C 具体表格进 Appendix D；Adaptive 只保留 conclusion 段落 |
| 人类独立数学审稿（Checklist item 10）Day 15 前仍未落实 | 50% | ★★★ | R&R 阶段诚实披露；不冒充；导师若无法安排则接受 poster 判定 |

---

## 六、Gate γ 判决标准（Day 15 EOD 触发条件）

**PASS** 必须同时满足：

- [ ] Suite A（AgentHarm）3 backbones × 8 modes × 2 subsets × n=200 全部出数
- [ ] Trust variant 4 档在 Llama-Guard 上出数
- [ ] Suite B 或 Suite C 至少一个 backbone × PG-full + backbone-only 对比出数
- [ ] Certificate empirical validity ≥ 4/5 seeds 在 dev-set 上通过
- [ ] 主稿 §7.1, §7.2, §7.4 数字入档；§7.3, §7.5, §7.6 至少骨架完整
- [ ] 无发现新的 leakage 类严重完整性 bug

**FAIL 触发条件（任一）：**

- LOBTO 下 PG-full 在 3 backbones 平均 benign FPR ≥ backbone 水平
- Certificate 在 dev-set 上 >2/5 seeds violate
- Suite B/C 全部无数据
- 计算预算破产（sweep 24h 未完成）

**FAIL 后果：**
- 首选：ICLR 2028（Sep 2026 截止，7 周后）
- 次选：NeurIPS 2027（May 2027 截止，10 个月后，可补 Suite C + 完整证书 sweep）
- 保底：COLM 2026（Aug 2026 截止，5 周后，8 页更宽松）

---

## 七、Response（CLAUDE.md §18）

**Decision or result.** Week 3 作为 sprint 决定性一周的完整执行路线已冻结。核心策略：Day 11 通过 LOBTO n=200 重跑判决 mechanism 是否 survive leakage 修复；Day 12 通过证书 empirical validity 判决 Gate β；Day 13-14 补 5 个 baseline mode 与 3-backbone 复现；Day 15 触发 Gate γ 判决。

**Evidence.** 计划所有具体数字均可追溯到 (a) `experiments/day10_audit_report.md` 的量化审计发现；(b) Sprint Dashboard 原时间表；(c) 论文 §7 骨架的 subsection 依赖关系。

**Files changed.** 
- `experiments/day10_audit_report.md`（Day 10 已写）
- `experiments/week3_execution_plan.md`（本文档，新建）
- `scripts/run_real_backbone_eval.py`（LOBTO + subgraph_signature + trust_variant patch）
- `precedentguard/guard.py`（query_subgraph_signature 参数）
- `tests/test_run_real_backbone_eval.py`（5 个新单测）
- `PrecedentGuard_AAAI27_Revised_Draft_v0.2.md`（§1.4 anchor + Contribution #3 + §7.1.a/b/c/d 重写）

**Validation performed.** 
- 165/165 单测通过（Day 6 的 160 + Day 10 修复的 5 个新增）
- LOEO n=200 数字用 stdlib 独立复算，与 JSONL 一致
- LOBTO 修复的正确性由新增 3 个单测 assert
- 主稿 §7.1.d 数字与 §7.1.a Table 1 相符

**Risks / limitations.** 
- (a) Day 11 LOBTO rerun 依赖用户 GPU，脚本延迟 4-6 小时；
- (b) 若 LOBTO 下 mechanism 失效，撤退到 NeurIPS 2027 意味着 5 周工作量重新配置；
- (c) 5 个新 baseline 的实现质量需在 Day 13 morning 前 code review；
- (d) 3-backbone 复现下若 ShieldGemma / Granite 表现异于 Llama-Guard，需要重新评估 "backbone-agnostic" 声明。

**Next highest-value action.** 
1. 用户在 Day 11 morning 复核 `experiments/day10_audit_report.md` 并签字判决 leakage；
2. 用户执行 `bash scripts/run_day7_agentharm_full_sweep.sh`（LOBTO patch 已合并到底层脚本）；
3. copilot 待 6 个新 JSONL 落地即刻更新 §7.1.b Table 2 并触发 Gate β 判决脚本。

---

**Plan version:** v1.0
**Sprint:** AAAI 2027 Week 3
**Anchor gates:** Gate β (Day 12 EOD), Gate γ (Day 15 EOD)
