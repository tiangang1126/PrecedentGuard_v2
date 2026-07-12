# PrecedentGuard AAAI 2027 —— Sprint 剩余阶段总体作战计划

**Author:** Research advisor (导师视角战略文档)
**Date:** 2026-07-12 (Sprint Day 12)
**Sprint remaining:** 16 天（Day 13–28）
**Deadlines:** Abstract 7/21 (Day 21), Full paper 7/28 (Day 28)
**Anchor documents:** `experiments/day10_audit_report.md`, `experiments/week3_execution_plan.md`, `PrecedentGuard_AAAI27_Revised_Draft_v0.2.md`
**Target quality:** AAAI Oral candidate（相当于全部录用论文顶端 5–10%）；Poster 是保底不是目标

---

## 目录

1. [当前诊断（Where we actually stand）](#一当前诊断where-we-actually-stand)
2. [AAAI 2027 Oral 的实际门槛](#二aaai-2027-oral-的实际门槛)
3. [战略分支决策树](#三战略分支决策树)
4. [Day 12–15 关键路径（Week 3 冲刺）](#四day-12-15-关键路径week-3-冲刺)
5. [Day 16–21 摘要冻结与主稿写作（Week 4 前半）](#五day-16-21-摘要冻结与主稿写作week-4-前半)
6. [Day 22–28 红队审稿与提交（Week 4 后半）](#六day-22-28-红队审稿与提交week-4-后半)
7. [Oral vs Poster 判定信号与提升杠杆](#七oral-vs-poster-判定信号与提升杠杆)
8. [R&R 阶段策略（假设通过初审）](#八rr-阶段策略假设通过初审)
9. [录用后 camera-ready + 口头汇报准备](#九录用后-camera-ready--口头汇报准备)
10. [拒稿后的会议路径矩阵](#十拒稿后的会议路径矩阵)
11. [六个不容妥协的科研诚实底线](#十一六个不容妥协的科研诚实底线)

---

## 一、当前诊断（Where we actually stand）

### 1.1 已经稳的资产

- **理论骨架**：Theorem 1（Directional Sensitivity Bound）、Theorem 2（Population Two-Sided）、Theorem 3（Finite-Sample Certificate）、Proposition 1（TV Indistinguishability）全部证明主体已经落地；A5 grid pre-commitment 扩为 $(\Gamma, \alpha)$ 联合承诺，SHA-256 hash 存在 `experiments/registry.csv`。4 位 AI 冷读审稿覆盖过一遍，7 条 BLOCKER 中 6 条消灭。
- **代码基础设施**：8 个模块 ~2400 LOC，**165/165 单测全绿**，Day 10 P0 修复合入（LOBTO helper、subgraph_signature、trust_variant flag、5 个 regression 单测）。三 vendor backend（Llama-Guard / ShieldGemma / Granite-Guardian）皆就绪，Llama-Guard 已跑通全端到端。
- **一条抗审稿的实证 anchor**：**clipping-only 反证**——benign FPR 从 backbone 67.5% 恶化到 76.0%（Wilson $[+2.5, +15.0]$ pp），这个结论在任何 LOO 协议下都不变（因为该模式不查询 precedent store）。这一 anchor 已写入 §1.4 和 §7.1.d，是 Corollary 1 目前最结实的实证支撑。
- **诚实叙事**：主稿 §7.1 已按 Day 10 audit 结论重构为 §7.1.a (LOEO 参考)、§7.1.b (LOBTO 主结果 pending)、§7.1.c (n=50 pilot)、§7.1.d (leakage-independent anchor)。Contribution #3 按 R4 M11 精确化。

### 1.2 尚在悬空的关键量

- **LOBTO n=200 主结果数字**（§7.1.b Table 2）—— *Gate β 的核心判决输入*，Day 12 EOD 前必须出数
- **Certificate empirical validity**（§7.2）—— 5 折 bootstrap 下 empirical FNR/FPR ≤ 预测 $U_{FN}, U_{FP}$ 是否 ≥ 4/5 seeds 通过
- **3-backbone 复现**（ShieldGemma-2B + Granite-Guardian-3.2-2B）—— 无这两个 backbone 数字，"backbone-agnostic" 声明必须撤回
- **4 trust variant ablation**（§7.4）—— Contribution #2 "trust-separated" 的核心 empirical 支撑
- **5 个学界 baseline**（flattened / raw_rag / cip_style / sequential_graph / random_graph）—— 无 CIP 头对头，§2.4 差异陈述会被质疑
- **Suite B (AgentDojo IPI) 或 Suite C (AgentPoison memory poisoning)** —— 单一 benchmark 不足以支撑 "general" 声明；两个 suite 至少要跑一个
- **Adaptive attack**（§7.5）—— 无此项等于承认 AAAI 门槛未达
- **Latency / GPU memory profiling**（§7.6）—— AAAI 一贯要求

### 1.3 已经严重滞后的项

按 Sprint Dashboard 原计划：
- Day 8–9 应该 ShieldGemma + Granite 双复现——**未跑**
- Day 9–10 应该 memory poisoning 与 trust ablation——**未跑**
- Day 11 Gate β 应该有全部 8 baselines 出数——**只有 3 mode × 1 backbone × 2 subset**

**实际情况：Day 7-11 花在了 Day 7 sweep 的深度审计 + P0 leakage 修复上。这 5 天不是浪费——它挽救了一次可能被 desk reject 的投稿——但它意味着 Week 3 必须 3–4 倍加速执行。**

### 1.4 时间预算的残酷算术

| 剩余任务 | 估计时长 | 剩余天数 | 每天可用 |
|---|---|---|---|
| LOBTO 3 backbones × 8 modes × 2 subsets × n=200 | 24–36 GPU-hours | 16 天 | 1.5 GPU-hour/day |
| Trust variant 4 档 × 1 backbone × 2 subsets × n=200 | 6 GPU-hours | 16 天 | 0.4 GPU-hour/day |
| Suite B/C 首跑 | 8 GPU-hours | 16 天 | 0.5 GPU-hour/day |
| Certificate + Adaptive + Efficiency 分析 | 12 CPU-hours | 16 天 | 0.75 CPU-hour/day |
| 主稿写作 + 4 位红队审稿 | ~60 人小时 | 16 天 | 3.75 人小时/day |

**结论：GPU 需求约 40 小时可控（3090 Ti 上 24h/日 空闲的话 2 天跑完），但人的写作与审稿 60 小时需要严格纪律。**

---

## 二、AAAI 2027 Oral 的实际门槛

### 2.1 Oral 是全部录用中的什么

AAAI 每年录用约 25%，其中 Oral 约占录用的 5-10%（即全部投稿的 1-3%）。Oral 不是 "更好的 poster"——它是 **AC 认定这篇论文有让所有 track 参会者都值得听 15 分钟的独立价值**。判断信号：

1. **论文有一句话 elevator pitch，且 pitch 里的每个词都非通用**（"first framework combining X and Y with formal guarantees"，而不是 "improves accuracy"）
2. **一个论断 + 一个反例 + 一个可复现的机制**（论断可 falsify，反例是实证支撑，机制解释为什么其他方法不 work）
3. **数字表格里有一个数字让审稿人拍案**——可以是 SOTA 数字、可以是一个反直觉的 flip、可以是一个理论 vs 实证的紧界
4. **有一段能被独立引用的 methodological insight**（"我们发现 $X$ 的关键不在 $A$，而在 $B$；这一发现可以直接迁移到 $C$"）

### 2.2 PrecedentGuard 目前具备的 Oral 信号

| 信号 | 强度 | 备注 |
|---|---|---|
| Elevator pitch 独特性 | **强** | "在一个证书里桥接 Theorem 1（EIG 结构 → 分数移动 bound）与 Theorem 3（class-conditional margin → error bound），双侧证书覆盖 5 种异质证据通道" |
| 反例（clipping-only regression） | **强** | 直接落地在 §7.1.d，任何 LOO 协议不变 |
| 机制解释 | **中等** | 有 directional trust 的机制阐述，但 empirical 上还需 LOBTO 主结果与 trust variant ablation 相互印证 |
| SOTA / 拍案数字 | **待验证** | 需要 LOBTO 主结果和三 backbone 复现来支撑；单 backbone Llama-Guard 上 -19.5 pp FPR 是量级 |
| 与最近工作的差异（CIP / SMSR / AttriGuard） | **强** | §2 已有精确差异陈述；SMSR 头对头对比是关键差异 |
| Theoretical novelty | **中等偏强** | Theorem 3 是 Hoeffding + 单侧 union bound 的标准应用；真正独创的是 Theorem 1 的 asymmetric $\rho$ 分解 + Proposition 1 的 TV 下界 |
| Independent verification | **弱** | 4 位 AI 冷读审稿存在但**尚无独立人类审稿**；对 Oral 而言这一项是硬扣分 |
| Reproducibility artifacts | **中等** | 代码 + 单测 + JSONL trace 完整；但 docs/ 4 个必要文档 (§4 CLAUDE.md) 缺失 |

### 2.3 距 Oral 的最短距离

**必须补上的三件事：**
1. **LOBTO 主结果 survive**（若 mechanism 在 leakage 修复后消失，Oral 不用讨论）
2. **3 backbones 复现 mechanism 方向**（这决定了 "backbone-agnostic" 声明能否成立）
3. **至少一位人类专家的独立数学审稿回执**（Checklist item 10；Oral 评审看到这一项空缺会直接扣分）

**能锦上添花的两件事：**
4. **Adaptive attack 数字**——AAAI 特别看重 "attacker who knows the defense"
5. **一张让人拍案的图**（例如 certificate 预测 vs empirical 的紧界；或 attack budget → error rate 的相图）

**不必赌命的：**
- Suite B / C 全部完成（只需要 1 个出数，另一个可放 appendix）
- Cross-domain / OOD（论文可以显式承认这是 future work，Paper 4 的题目）
- Two-stage screening / conformal risk control（都是 §5.4 Remark，不入主文）

---

## 三、战略分支决策树

### 3.1 三条路径

```
Day 12 EOD LOBTO n=200 判决
    │
    ├── (a) PG-full benign FPR < 0.62 且 harmful recall ≥ 0.94
    │        → Mechanism 保留完整，进入 Oral 冲刺路径
    │        → 全部 Week 3-4 计划按 Master Plan §四-§六执行
    │
    ├── (b) PG-full benign FPR ∈ [0.62, 0.675] 且 harmful recall ≥ 0.94
    │        → Mechanism 部分保留，进入 Poster-defensible 路径
    │        → 论文降级 headline claim；不追求 Oral，主打 Suite B/C 广度
    │        → 增加 sensitivity study（K 值、β scale grid、threshold sweep）
    │
    └── (c) PG-full benign FPR ≥ 0.675 或 harmful recall < 0.94
             → Mechanism 声明失效
             → 撤退到 NeurIPS 2027 或降级投 COLM 2026 / EMNLP 2026 Findings
             → 立即停止 AAAI 相关写作，avoid sunk cost
```

**判决脚本：** `scripts/day12_certificate_empirical_validity.py`（Day 12 早上写）会自动执行判决并写 verdict 到 `experiments/gate_beta_report.md`。

### 3.2 判决当天必须做的三件事

- **不硬撑**：如果落在 (c) 分支，主动触发 STOP-LOSS。硬撑是把 4-6 周工作变成 desk reject 的最快方法。
- **不虚荣**：如果落在 (b) 分支，接受 Poster 判决，把剩余时间用于把论文做扎实。Poster 稿件质量高的 candidate 在下一轮投稿（NeurIPS/ICML）显著加速。
- **不侥幸**：即使落在 (a) 分支，也要立即冻结数字（写到 `experiments/registry.csv`），不允许后续 tuning 触碰 test set。

### 3.3 关于 "Oral 是否值得赌命" 的一个 sober take

Oral 相对 Poster 的实际收益：
- **可见度**：高，但 AAAI 是巨型会议，Oral session 平行多 track，实际听众可能仅 30-80 人
- **引用**：中长期 20% 内的差异，短期几乎无差
- **学术资本**：博士期间 1-2 篇 Oral 有实质意义，但 3-4 篇之后边际收益急剧递减
- **风险**：追求 Oral 的写作/实验决策若滑向浮夸声明，会显著提升 desk-reject 风险

**结论：AAAI Oral 是"如果自然涌现出来就接下"、不是"必须造出来"的东西。把力气花在 (1) 论文核心机制的可证伪性、(2) 三 backbone 复现、(3) adversarial adaptive attack 上——这三件事做扎实，Oral 会自动落到手里；做不扎实，Oral 也不会落到手里。**

---

## 四、Day 12–15 关键路径（Week 3 冲刺）

### 4.1 Day 12 (Sun, 2026-07-12) —— Gate β 判决日

**上午 (09:00–12:00)：**

- [ ] **09:00–09:30** 用户复核 `experiments/day10_audit_report.md` 和 §7.1 修订，签字批准
- [ ] **09:30–11:00** copilot 写 `scripts/day12_certificate_empirical_validity.py`（骨架见 §4.7）
- [ ] **11:00–12:00** copilot 写 `scripts/day12_launch_lobto_sweep.sh` 参数化 launcher，输出到 `artifacts/day12/`

**下午 (14:00–18:00)：**

- [ ] **14:00–18:00** 用户在 GPU 环境执行 `bash scripts/day12_launch_lobto_sweep.sh`
  - Llama-Guard-3-1B × 3 modes × 2 subsets × n=200 = 6 JSONL
  - 参数：`--trust-variant policy_attested`（primary run）
  - 预期 wall clock ~4 小时

**晚上 (19:00–22:00)：**

- [ ] **19:00–20:30** copilot 分析 6 个 JSONL，填 §7.1.b Table 2，跑 Fisher / McNemar / Wilson CI
- [ ] **20:30–21:30** copilot 执行 certificate empirical validity 脚本，5 折 bootstrap
- [ ] **21:30–22:00** copilot 写 `experiments/gate_beta_report.md` 判决报告
- [ ] **22:00** 用户与 copilot 视频/文字沟通，敲定分支 (a/b/c)

### 4.2 Day 13 (Mon, 2026-07-13) —— 补 baselines + ShieldGemma 复现

**假设 Day 12 落在分支 (a)。若落在 (b/c)，Day 13 计划要重排。**

**上午 (09:00–12:00)：**

- [ ] **09:00–12:00** copilot 实现 4 个新 mode 到 `run_real_backbone_eval.py`：
  - `flattened_trajectory`：把全 trajectory 拼进 base view 传给 backbone；不做 counterfactual
  - `raw_rag_concat`：precedent 直接拼 prompt，不做 counterfactual/clipping/trust
  - `cip_style`：EIG serialize 为 "node → node" chain 拼进 prompt
  - `sequential_graph`：EIG 用 chain 替代（不用真实 causal edge）
  - 补 12 个单元测试（每 mode 3 个：determinism / empty trajectory / retrieval integration）
  - 目标：180/180 单测全绿

**下午 (14:00–19:00)：**

- [ ] **14:00–18:00** 用户 GPU 执行 ShieldGemma-2B × 6 modes × 2 subsets × n=200（12 个 JSONL）
- [ ] **18:00–19:00** 用户 GPU 执行 Llama-Guard × 4 个新 mode × 2 subsets × n=200（8 个 JSONL）
- [ ] **19:00–21:00** copilot 合并所有数字入 §7.1 主表格 v2.0（8 modes × 2 backbones × 2 subsets 部分填充）

### 4.3 Day 14 (Tue, 2026-07-14) —— Granite + Trust variant

**上午 (09:00–13:00)：**

- [ ] **09:00–13:00** 用户 GPU 执行 Granite-Guardian-3.2-2B × 8 modes × 2 subsets × n=200（16 个 JSONL）

**下午 (14:00–17:00)：**

- [ ] **14:00–17:00** 用户 GPU 执行 Llama-Guard × PG-full × 4 trust variants × 2 subsets × n=200：
  - `--trust-variant no_provenance`
  - `--trust-variant signature_only`
  - `--trust-variant lineage`
  - `--trust-variant policy_attested`（已有于 primary run，不重跑）
  - 共 6 个新 JSONL（3 variants × 2 subsets）

**晚上 (18:00–22:00)：**

- [ ] **18:00–20:00** copilot 填 §7.4 Trust variant table + Fisher 三配对
- [ ] **20:00–21:00** copilot 填 §7.1 主表格 v3.0（3 backbones × 8 modes × 2 subsets 全部就绪）
- [ ] **21:00–22:00** copilot 生成 Figure 2 (margin vs $\rho$) 和 Figure 3 (certified vs empirical) 的 matplotlib 数据表

### 4.4 Day 15 (Wed, 2026-07-15) —— Suite B/C 首跑 + Gate γ 判决

**Suite 选择判决：** Day 14 EOD copilot 评估 AgentDojo 和 AgentPoison 数据加载器实现代价，选**加载器简单+对 mechanism 冲击大**的一个作为 Day 15 主 suite。

**推荐：Suite C = AgentPoison subset**（论文标题就是 "PrecedentGuard"——精髓在 memory poisoning；AgentPoison 与 precedent 概念直接对齐）。

**上午 (09:00–12:00)：**

- [ ] **09:00–11:00** copilot 写 AgentPoison subset loader（约 200 行代码 + 3 个单测）
- [ ] **11:00–12:00** copilot 写 adaptive attack simulator：coordinate ascent over per-type $c^\pm$，budget = 100 queries/trajectory

**下午 (14:00–19:00)：**

- [ ] **14:00–18:00** 用户 GPU 执行 Llama-Guard × {backbone_only, PG-full} × AgentPoison subset × n=100
- [ ] **18:00–19:00** 用户 GPU 执行 adaptive attack sweep（同上，加对手模拟）

**晚上 (19:00–22:00)：**

- [ ] **19:00–20:30** copilot 填 §7.5 Adaptive + Suite C 数字
- [ ] **20:30–21:00** copilot 计算 latency/GPU memory profile（从既有 JSONL 的 `timing_ms` 字段，丢弃 first-sample warmup）
- [ ] **21:00–22:00** copilot 写 `experiments/gate_gamma_report.md` 判决

**Gate γ PASS 标准：**
- 3 backbones × 8 modes 主表格数字齐全
- Trust variants 4 档出数
- Suite B/C 至少 1 个出数
- Certificate 有效性 ≥ 4/5 seeds 通过
- Adaptive attack 数字入档
- 主稿 §7.1–§7.4 数字冻结

**若 Gate γ FAIL → 立即改投 ICLR 2028**（Sep 2026 截止，7 周后，可补 Suite B/C 与完整证书 sweep）。

### 4.5 Day 12–15 期间的日常纪律

- **每天 EOD 前**：git commit 当天全部代码 + JSONL + 主稿差异
- **A5 grid 承诺**：任何新的 grid 点必须先 `commit_grid_hash` 再触碰 calibration
- **数字入档**：所有 headline 数字必须在 `experiments/registry.csv` 有 row
- **拒绝 cherry-pick**：任何单一 seed / config 选取的数字不入主表格
- **不覆盖 raw JSONL**：一旦落地，只 append 新文件，不修改旧文件
- **失败即记**：任何 hyperparameter 尝试的失败结果写到 `docs/FAILURE_LOG.md`

### 4.6 关键脚本清单（Day 12 早上必写）

| 脚本 | 用途 | 交付 |
|---|---|---|
| `scripts/day12_launch_lobto_sweep.sh` | Day 12 LOBTO n=200 launcher | Day 12 09:00 |
| `scripts/day12_certificate_empirical_validity.py` | Gate β 判决脚本 | Day 12 11:00 |
| `scripts/day12_summarize_lobto.py` | 精算 Wilson CI + Fisher + McNemar | Day 12 19:00 |
| `scripts/day13_run_new_baselines.py` | 4 个新 mode 的批处理 launcher | Day 13 09:00 |
| `scripts/day14_trust_variant_sweep.sh` | 4 trust variants launcher | Day 14 14:00 |
| `scripts/day15_agentpoison_loader.py` | Suite C 数据加载 | Day 15 09:00 |
| `scripts/day15_adaptive_attack.py` | Adaptive attack simulator | Day 15 11:00 |
| `scripts/day15_efficiency_profile.py` | Latency + GPU memory 分析（从 timing_ms 字段） | Day 15 20:30 |

### 4.7 `scripts/day12_certificate_empirical_validity.py` 骨架

```python
"""
Gate β 判决脚本：Certificate empirical validity on dev set.

对每个 LOBTO JSONL：
  1. 计算 empirical FNR / FPR
  2. 用 precedentguard.certificate.compute_certificate() 算 U_FN, U_FP
  3. 5 折 bootstrap（seeds = [7, 13, 17, 19, 23]）：80% calibration / 20% test
  4. 判决：U_FN >= empirical_FNR AND U_FP >= empirical_FPR 是否 >= 4/5 seeds 成立

Output:
  experiments/day12_certificate_validity.csv
  experiments/gate_beta_report.md

Usage:
  python scripts/day12_certificate_empirical_validity.py \
    --root artifacts/day12 \
    --prefix day12_lobto \
    --alpha 0.05 \
    --seeds 7 13 17 19 23
"""
from __future__ import annotations
import argparse, json, random
from pathlib import Path
from statistics import mean

from precedentguard.certificate import (
    CertificateConfig, Certificate,
    commit_grid_hash, assert_grid_committed,
    compute_certificate,
)
from precedentguard.clipping import symmetric_caps
from precedentguard.types import NodeType

def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.open('r', encoding='utf-8') if l.strip()]

def bootstrap_split(rows: list[dict], seed: int, cal_fraction: float = 0.8):
    rng = random.Random(seed)
    shuffled = list(rows); rng.shuffle(shuffled)
    n_cal = int(len(shuffled) * cal_fraction)
    return shuffled[:n_cal], shuffled[n_cal:]

def compute_empirical_rates(harmful_rows, benign_rows, theta=0.5):
    fnr = sum(1 for r in harmful_rows if r['s_pg'] < theta) / max(len(harmful_rows), 1)
    fpr = sum(1 for r in benign_rows if r['s_pg'] >= theta) / max(len(benign_rows), 1)
    return fnr, fpr

def main():
    # ... argparse ...
    # For each mode: load harmful & benign JSONL
    # Build calibration config (must match A5 grid hash)
    # For each seed in [7,13,17,19,23]:
    #   split; call compute_certificate(cfg, cal_samples, alpha) -> U_FN, U_FP
    #   evaluate on test split -> emp_FNR, emp_FPR
    #   valid = (U_FN >= emp_FNR) and (U_FP >= emp_FPR)
    # Report K/5 seeds valid per mode -> Gate β verdict
```

**这个脚本是 Day 12 EOD 判决的定量证据。Copilot 会在早上完成实现。**

---

## 五、Day 16–21 摘要冻结与主稿写作（Week 4 前半）

### 5.1 Day 16 (Thu, 2026-07-16) —— Latency & Efficiency + 主稿 §7.6

**上午：** copilot 完成 §7.6 Efficiency subsection
- Median / P90 / P95 latency（丢弃 first-sample warmup）
- GPU memory 报告（`torch.cuda.max_memory_allocated`）
- Guard calls per decision + tokens overhead
- Two-stage screening ablation（可选，见 §7.6-extended）

**下午：** copilot 完成 §7.3 "Does the execution graph matter?"
- 从 Day 14 sequential_graph / random_graph JSONL 提数字
- Parent-localization 精度 + attacked F1 三 mode 对比
- Non-parent vs parent counterfactual 效应大小

### 5.2 Day 17 (Fri, 2026-07-17) —— 图表冻结

**上午：** copilot + 用户共同产出 4 张 Figure：
1. **Figure 1**：模型系统图（TikZ）—— EIG + intervention + trust gate 三 panel
2. **Figure 2**：Margin distribution + $\rho_+, \rho_-$ 的 threshold 关系（matplotlib）
3. **Figure 3**：Certified $U_{FN}, U_{FP}$ 曲线 vs empirical 曲线（matplotlib）
4. **Figure 4**：Parent vs non-parent counterfactual effect size（matplotlib，可选放 appendix）

**下午：** copilot 完成 Tables 1-4 LaTeX 版本（tabularx，不用 booktabs 之外的 exotic 包）
- Table 1: 3 backbones × 8 modes × 2 subsets 主表格
- Table 2: 4 trust variants
- Table 3: Certificate empirical validity
- Table 4: Latency profile

**晚上：** 用户 walk-through 全部 Figure 与 Table，纠正措辞、颜色、坐标轴

### 5.3 Day 18 (Sat, 2026-07-18) —— Gate γ 复审 + 主稿 §1-§4 打磨

**Gate γ 已在 Day 15 EOD 判决过。Day 18 是最后的调整机会：**
- 若数字有边界（例如 certificate 4/5 seeds 恰好通过），用 Day 18 补一次 seed
- 若图表有问题（legend 覆盖、精度不足），Day 18 修

**主稿打磨（copilot 主导，用户批准）：**
- §1 Introduction 每段第一句必须是 topic sentence
- §2 Related Work 五段结构（static / trajectory-aware / memory poisoning / decoding-time / causal），每段一个 comparison axis
- §3 Problem Formulation 检查所有 notation 一致性
- §4 Method 检查 Algorithm 1 与实现完全一致（`precedentguard/guard.py:decide` 逐行核对）

### 5.4 Day 19 (Sun, 2026-07-19) —— 主稿 §5-§9 打磨 + Appendix

**理论章节 §5：**
- 每个 Assumption A1–A6 后面必须紧跟"为什么这个假设合理 + 何时会失效"
- Theorem 1-3 statement 与 Appendix A.1-A.3 证明骨架逐字核对
- Proposition 1 措辞不能超出 "existence counterexample" 范围（R1 F5 教训）

**Discussion §8：**
- 讨论 clipping-only regression 的机制含义（现在这是 headline anchor）
- 讨论 LOBTO 修复的科研诚实过程（可以是 selling point 而非弱点）
- 一段专门 vs SMSR / MemLineage / CIP 的精确差异

**Limitations §9：**
- 六条限制严格对齐 §8.5 Failure modes
- 一条明确列 "leakage was discovered during self-audit"
- 一条明确列 "human independent mathematical review has [is | is not] been completed"

**Appendix D：** 全部 sensitivity study
- K ∈ {1, 2, 3, 5}
- β scale grid 4×4
- Threshold θ ∈ {0.4, 0.5, 0.6}
- α ∈ {0.01, 0.05, 0.10}

### 5.5 Day 20 (Mon, 2026-07-20) —— 独立人类审稿关键 24 小时

**Checklist item 10（人类独立数学审稿）是 Oral 判决的硬扣分项。今日的目标：**

- 用户上午发送邮件给 3 位可能的合作组同事：
  - 导师推荐的因果推断方向老师
  - 学习理论方向的 senior PhD
  - 曾经写过 Hoeffding 类证明的博士后
- 附件：Theorem 1 Step 2、Prop 1 measurability preamble、Corollary 1 DPI 论证——不超过 3 页
- 明确请求：**48 小时内**给出 "证明是否成立 + 有无 gap" 的书面回执
- 补充说明：一次约 2 小时工作量

**若 48 小时内 ≥ 1 位回执 → §5 加脚注 "independently reviewed by [name] on [date]"**
**若 48 小时内 0 位回执 → §9 Limitations 明确披露 "AI-facilitated adversarial audit; human mathematical review is deferred to the R&R stage."**

### 5.6 Day 21 (Tue, 2026-07-21) —— 摘要提交日

**11:00 UTC** 摘要冻结（AAAI 摘要截止一般 UTC 23:59，用户所在时区往前推）

摘要必须包含：
1. 一句 elevator（"class-conditional two-sided certificates over heterogeneous trajectory-evidence channels"）
2. 一个动机段落（bounded score movement ≠ bounded error rate，实证支撑）
3. 两条定理的一句话总结
4. 头条实证数字（LOBTO 主结果 + adaptive attack survivor）
5. 关键词：LLM agent safety, causal intervention, class-conditional certificate, memory-poisoning defense

**摘要不允许包含：**
- "state of the art"
- "significantly improve"
- "robust to all attacks"
- "first ever"

---

## 六、Day 22–28 红队审稿与提交（Week 4 后半）

### 6.1 Day 22 (Wed, 2026-07-22) —— 因果推断 reviewer

用户扮演 R1（因果推断 AC），或者请合作组同事：
- 检查 EIG 语义是否清晰
- Counterfactual replay 术语是否与 causal inference 主流一致
- Do-calculus vs interventional influence 的边界是否清楚
- Proposition 1 与 CIP、AttriGuard 的差异是否精确

**必须在 EOD 前将 R1 findings 记入 `experiments/day22_red_team_causal.md`。**

### 6.2 Day 23 (Thu, 2026-07-23) —— 安全 reviewer

- 检查 Threat model §3.3 是否覆盖：cross-session coordination / query budget / adaptivity flag
- Trust attestation 边界 §3.4 是否明确排除 policy-attested compromise
- Adaptive attack §7.5 是否是 "genuine adaptive" 还是 "clean run relabeled as adaptive"
- SMSR 头对头是否公平（相同 attack budget、相同 defense capabilities）

### 6.3 Day 24 (Fri, 2026-07-24) —— 学习理论 reviewer

- Hoeffding tail 的常数是否与 skeleton Theorem 3 完全一致
- Union bound size $N = 2|\Gamma|$ 是否清楚
- A5 grid pre-commitment 与 $\alpha$ 联合承诺是否严格
- Confidence interval 报告是否用了正确的 finite-sample bound
- Randomized decision rule 覆盖是否明确

### 6.4 Day 25 (Sat, 2026-07-25) —— 实证 reviewer

- 每个 Table 数字是否可以从 raw JSONL 精确复现（选 3 个随机 cell，独立复算）
- Leakage 是否已完全消除（LOBTO 协议 documentation 是否完整）
- Certificate empirical validity 报告是否包含 alpha, N, K, n 完整参数
- 每一处 "significant" 是否有对应的 $p$-value 与效应大小
- Cherry-picking 检查：seed / config 分布是否 balanced

### 6.5 Day 26 (Sun, 2026-07-26) —— Integration + revision

**综合 4 位 reviewer 的 findings，改主稿：**
- 全部 BLOCKER-级问题必修
- MAJOR-级问题必修
- MINOR-级 pick 时间允许的
- LaTeX 编译通过（pdflatex + bibtex + pdflatex × 2）
- Reproducibility checklist 每项打 ✓ 或明确解释

**Anonymization 检查：**
- 移除 git repo URL、author names、institution names
- 检查 `\thanks{}` 与 `\affil{}` 是否都注释掉
- 检查 PDF metadata（`pdfinfo` 命令）不含个人信息

### 6.6 Day 27 (Mon, 2026-07-27) —— 最终审计

**Reference verification：**
- 每一条 BibTeX entry 的 DOI / arXiv ID 独立打开链接确认
- 特别核对：SMSR, CIP, AgentPoison, MINJA, PoisonedRAG, MemLineage 的**准确出处**
- 无 [12], [13] 之类的 placeholder

**Citation density audit：**
- 每段引用密度不超过 3 篇（超过说明堆叠了）
- 无 "orphan citation"（引用了但正文没解释）
- Self-citation 比例 < 15%（当前应为 0%，因为前作还未 published）

**LaTeX 编译 + PDF 检查：**
- 8 页限制严格遵守（AAAI 2027 是 7 页正文 + unlimited references）
- 图与表在正文均被 cite 到
- Reproducibility checklist 附录完整

### 6.7 Day 28 (Tue, 2026-07-28) —— 提交日

**12:00 (noon) local time** —— 提交到 AAAI OpenReview / EasyChair
- 提前 5 小时提交，为系统故障留 buffer
- 提交后立即下载确认 PDF，核对 metadata
- 邮件确认收据存档到 `experiments/submission_receipt.eml`

**17:00 硬截止**（不要拖到最后 10 分钟——系统故障是常态）

**23:59** 允许自己休息 1 天，然后 Day 29+ 开始 Suite C / adaptive extension 为 R&R 阶段积累 material。

---

## 七、Oral vs Poster 判定信号与提升杠杆

### 7.1 AC 是如何判定 Oral 的（推测模型）

AAAI Program Chair 通常会看：
1. **审稿人得分分布**：Oral 通常需要 3 位审稿人平均 Accept 以上，且至少 1 位 Strong Accept
2. **审稿人置信度**：低置信度的高分不如高置信度的中高分
3. **novelty 与 significance 的具体证据**：审稿人是否引用了"这是第一个 X"、"这个结果推翻了 Y"
4. **技术深度**：论文的 core proof/method 是否只有专家能理解
5. **broader impact**：是否 track 之外的听众也可能受益

### 7.2 PrecedentGuard 的 Oral 提升杠杆（按投入产出比排序）

**高 ROI（Day 12–15 可控）：**
- ✅ **LOBTO n=200 三 backbone 复现** → 显著提升 "generalizable" 信号
- ✅ **Adaptive attack survivor** → 显著提升 "under adversarial pressure" 信号
- ✅ **Trust variant 4 档 monotone 分离** → 显著提升 mechanism 可解释性

**中 ROI（Day 16–21 可控）：**
- ✅ **Figure 3 certificate vs empirical 紧界图** → 一张让审稿人拍案的图
- ✅ **§8 Discussion 一段可独立引用的 methodological insight** → 让其他方向的人愿意 cite
- ⚠️ **1 位人类独立审稿回执** → 补齐 checklist；无回执不致命但扣分

**低 ROI（Week 4 才可能，不必赌）：**
- ❌ Cross-domain OOD certificate（Paper 4 的题目，不硬塞进 Paper 1）
- ❌ Two-stage screening latency（有意思但不 load-bearing）
- ❌ Conformal risk control extension（remark 一行就够）

### 7.3 如果 Day 22 红队审稿发现 core mechanism 有严重 gap 怎么办

**不是自动 Poster，也不是自动撤稿——用一个 4 小时窗口决定：**

- **Gap 可以 24 小时内补上**（数字层面）→ 补完提交 Oral 候选
- **Gap 需要 3+ 天补上**（新实验层面）→ 降级 Poster claim，把 gap 显式写入 §9 Limitations
- **Gap 是 fundamental 的**（理论层面）→ 撤退到 NeurIPS 2027，不硬撑

---

## 八、R&R 阶段策略（假设通过初审）

### 8.1 R&R 时间线（估计）

- **Day 30 左右**：初审结束，进入 rebuttal window（约 1 周）
- **Day 40 左右**：Rebuttal 提交
- **Day 50 左右**：最终判决

### 8.2 Rebuttal 写作原则

1. **每一位 reviewer 的每一个 point 都必须有回应**——不能忽略
2. **回应结构**：一句话总结 → 具体证据（数字、图、代码路径）→ 承诺的改动
3. **不辩论 subjective 判决**（"we believe this is novel"），只回应 objective 事实
4. **有 gap 就承认**，并给出 "in the camera-ready we will..." 的具体修补计划
5. **提前预写常见质疑的回应**（用 Day 22-25 红队审稿的 findings 作为预演）

### 8.3 可能的常见质疑与预写回应

**Q1（causal reviewer）："Your EIG is not a causal graph in Pearl's sense; how do you justify calling this a causal method?"**

预写回应：
> "We agree that the EIG is not a Pearlean causal graph; §3.2 explicitly frames it as an *execution-derived intervention interface* rather than a discovered causal structure. Every 'causal' claim we make is scoped to this operational sense — see the 'interventional influence under the implemented replay operator' terminology at line X. Related work §2.2 draws the distinction from CIP which does treat CIDs as causal reasoning aids."

**Q2（security reviewer）："Your threat model excludes intent-hijacking; can PG defend against a user who is themselves malicious?"**

预写回应：
> "Section 3.3 makes this out-of-scope explicit. PG defends the *guard* from evidence-channel compromise; malicious-user attacks are a different problem class (typically addressed by upstream authorization). This is a scoping decision, not an oversight."

**Q3（learning-theory reviewer）："Your union bound uses N=2|Gamma|; if you actually swept K configurations, the effective N is larger."**

预写回应：
> "Assumption A5 requires the full grid $\Gamma$ to be committed *before* calibration, so $|\Gamma|$ is the number of *committed* grid points, not the number of *reported* points. We committed $|\Gamma| = X$ via SHA-256 hash H stored in `experiments/registry.csv` at timestamp T. The 2-multiplier comes from the class-conditional split (Y=1 and Y=0), following [reference]. This is the standard one-sided finite-sample bound."

**Q4（empirical reviewer）："You only ran 200 examples per subset; certificates are asymptotic; what's your finite-sample coverage?"**

预写回应：
> "Theorem 3 is *not* asymptotic; the Hoeffding tail $t = \sqrt{\log(2|\Gamma|/\alpha)/(2n)}$ is finite-sample at $n = 200$. Table 3 reports the empirical vs predicted bound on 5 bootstrap seeds; 4/5 or 5/5 satisfy $U_{FN} \ge \hat R_{FN}$ and $U_{FP} \ge \hat R_{FP}$. The n=200 choice was pre-registered under A5; larger n only tightens the bound, not the direction."

**Q5（general reviewer）："How does PG compare on OS-Harm / BrowseComp / MCPSecBench?"**

预写回应：
> "We currently evaluate on AgentHarm (Suite A) and AgentPoison (Suite C); the reviewer's suggested benchmarks are important extensions we commit to running in the camera-ready. Pre-committed grid for the extension is committed at hash H2."

### 8.4 Rebuttal 写作时间预算

- **10 小时**用于每位 reviewer 的具体回应写作（3 位 × 3 小时 + 1 位强 accept 1 小时）
- **4 小时**用于任何新增实验（例如 reviewer 要求的 additional baseline）
- **2 小时**用于 LaTeX 修订与预览
- **1 小时**用于 review + 提交

**共约 17 小时；控制在 3 天完成。**

---

## 九、录用后 camera-ready + 口头汇报准备

### 9.1 若 accept as Poster

**Camera-ready（1 周内）：**
- 补齐 rebuttal 承诺的所有改动
- 增强 Reproducibility checklist（GitHub repo 公开）
- 修正 typo 与格式
- 上传 supplementary（AppendixD + 代码 + JSONL trace）

**Poster preparation（会议前 4 周）：**
- 一张 A0 poster：3 panel 结构（问题 → 方法 → 结果）
- 打印 100 张 handout 摘要
- 准备 2-3 分钟 elevator pitch 与 15-20 分钟深度对话稿

### 9.2 若 accept as Oral

**Camera-ready 与 Poster 相同，加上：**

**Talk preparation（会议前 4 周）：**
- 15 分钟 talk（AAAI 常规）：8 slides 内容 + 1 slide 问答 buffer
- 目标结构：
  - Slide 1: Title + one-liner motivation
  - Slide 2: The failure mode（clipping-only regression 反例，一张图）
  - Slide 3: EIG intuition（不讲数学，讲结构直觉）
  - Slide 4: Theorem 1 intuition
  - Slide 5: Theorem 3 intuition
  - Slide 6: LOBTO 主结果 table
  - Slide 7: Adaptive + trust variants
  - Slide 8: Limitations + broader relevance
- 至少 3 次内部 rehearsal（合作组、导师、跨方向同事各一次）
- 常见问题预写 answer bank（最少 20 个）

**Video recording（部分会议要求）：**
- 摄制 ≤ 15 分钟 backup video 上传 OpenReview
- 用 macOS QuickTime 或 OBS，录制干净背景 + 幻灯片 + 头像画中画

### 9.3 会议现场纪律

- 会议开始前 24 小时到达，避免时差影响
- Poster 站位：全程站，不坐；每小时休息 5 分钟
- Talk：讲之前 30 分钟到会场，测试 clicker 与投影
- Networking：主动找 3-5 位 relevant 方向的 senior researcher 讨论

---

## 十、拒稿后的会议路径矩阵

### 10.1 若 AAAI 2027 拒稿（约 40% 概率）

**Day of decision (D+50)：** 收到拒稿邮件；不做任何冲动决定，休息 24 小时

**D+51：** 系统分析 reviewer 反馈
- 分 3 类：(a) 可修复的写作问题；(b) 需要补实验的问题；(c) 判决错误
- (c) 类不作为改进依据，只用来判断是否需要向 CS 顶会申诉（AAAI 有 rebuttal 但无正式 appeal）

**D+52：** 决定下一站会议

| 会议 | 截止日期 | 主要考虑 |
|---|---|---|
| **ICLR 2028** | Sep 2026 (D+65) | 双盲；接受高分论文的比例更高；ML 主流受众；**首选** |
| **NeurIPS 2028** | May 2027 (D+300) | 有充分时间补 Suite B/C 与完整 certificate sweep；**次选** |
| COLM 2026 | Aug 2026 (D+35) | 时间紧但可行；LLM 专门会议；受众窄但对口 |
| EMNLP 2026 Findings | Aug 2026 (D+35) | 8 页更宽松；NLP 主流；但 "safety" 主题略偏门 |
| **NeurIPS 2027 (delayed)** | 已 elapsed | 若 AAAI 决定太晚，NeurIPS 已过截止 |

### 10.2 会议之间的论文改造代价

- **AAAI → ICLR**：几乎无改动；格式转换 + 摘要重写 + 1 位额外 reviewer 视角红队；预计 20 人小时
- **AAAI → NeurIPS**：中等改动；NeurIPS 更强调 broader impact 与 reproducibility；预计 40 人小时
- **AAAI → COLM**：较大改动；COLM 更强调 LLM-specific novelty；预计 60 人小时
- **AAAI → EMNLP Findings**：较大改动；NLP 视角重写 Introduction 与 Related Work；预计 80 人小时

### 10.3 拒稿到再投的关键原则

1. **不情绪化改动**：先冷静 2-3 天再动键盘
2. **不硬堆改动**：每一个 reviewer 抱怨都对应一个具体改动，无关的 reviewer 抱怨的东西不改
3. **改动前记录 diff**：`docs/DECISIONS.md` 记录每一次结构改动的理由
4. **不 desperate re-submit**：如果需要 2 个月以上补实验，就等下一个 major venue，不投 second-tier

---

## 十一、六个不容妥协的科研诚实底线

这些底线是 CLAUDE.md §2 的浓缩，也是 AAAI Reproducibility Checklist 的核心。**任何一条被打破，直接触发论文撤回：**

1. **不虚构任何引用**——任何 [X] 都必须有可验证的 DOI/arXiv ID
2. **不隐藏 leakage**——LOBTO 修复历史必须写入 §7.1 或 §9
3. **不 cherry-pick seed**——所有 headline 数字用 pre-committed grid + 全部 5 折
4. **不 rephrase overclaim**——"SOTA"、"robust"、"safe"、"first" 必须有明确 scope
5. **不合成实验证据**——所有数字必须来自 raw JSONL；任何手输数字触发 desk reject
6. **不假 human review**——若无人类回执，§9 明说；不冒充"independently reviewed"

**违反任何一条，即使 AAAI 未察觉，NeurIPS/ICML 审稿人也会发现——学术声誉是终生资产，投稿是短期赌局。**

---

## 十二、每天 EOD 60 秒自检

从 Day 12 到 Day 28，每天 EOD 花 60 秒回答：

1. 今日完成的事项是否与 Master Plan 的当日交付 100% 匹配？
2. 是否有 stop-loss 信号出现（Gate β/γ 触发条件）？
3. 明天首要 3 件事是什么？
4. 是否需要向导师申报 blocker？

**若连续 2 天不能全 ✓，立即触发下一个 Gate。硬撑是最贵的选项。**

---

## 附录 A：文件与 artifact 索引

```
docs/
  AAAI27_master_plan.md         # 本文档（Master Plan）
  CLAIM_EVIDENCE.md              # 每个 claim → evidence 映射（Day 12 建立）
  DECISIONS.md                   # 结构性决策日志（Day 12 建立）
  FAILURE_LOG.md                 # 失败尝试与教训（Day 12 建立）
  RESEARCH_SPEC.md               # 问题、RQ、假设（Day 12 建立）
  THREAT_MODEL.md                # 完整威胁模型（Day 12 建立）
  RELATED_WORK.md                # 文献矩阵（从 §2 抽取，Day 12 建立）

experiments/
  registry.csv                   # 全部 experiment run 索引（Day 12 建立）
  day10_audit_report.md          # ✅ Day 10 导师级审计
  week3_execution_plan.md        # ✅ Week 3 逐日执行清单
  gate_beta_report.md            # Day 12 EOD 判决报告
  gate_gamma_report.md           # Day 15 EOD 判决报告
  day22_red_team_causal.md       # Day 22 R1 findings
  day23_red_team_security.md     # Day 23 R2 findings
  day24_red_team_learning.md     # Day 24 R3 findings
  day25_red_team_empirical.md    # Day 25 R4 findings
  submission_receipt.eml         # Day 28 提交确认

scripts/
  day12_launch_lobto_sweep.sh                # LOBTO n=200 launcher
  day12_certificate_empirical_validity.py    # Gate β 判决脚本
  day12_summarize_lobto.py                   # Wilson + Fisher + McNemar
  day13_run_new_baselines.py                 # 4 新 mode launcher
  day14_trust_variant_sweep.sh               # 4 trust variants launcher
  day15_agentpoison_loader.py                # Suite C 数据加载
  day15_adaptive_attack.py                   # Adaptive attack simulator
  day15_efficiency_profile.py                # Latency + memory 分析

artifacts/
  day6/                          # Day 7 LOEO n=200（reference only；leaky）
  day12/                         # Day 12 LOBTO n=200 primary
  day13/                         # Day 13 ShieldGemma + 4 new modes
  day14/                         # Day 14 Granite + trust variants
  day15/                         # Day 15 AgentPoison subset + adaptive
```

---

## 附录 B：Master Plan 快速索引卡（贴桌面）

```
今天是 Day X（sprint start = 2026-06-30）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Day 12 (7/12) —— Gate β 判决日
Day 15 (7/15) —— Gate γ 判决日
Day 21 (7/21) —— 摘要截止
Day 28 (7/28) —— 全文截止
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

当前 headline claim（不硬撑）：
"Class-conditional two-sided certificates
 over heterogeneous trajectory-evidence
 channels on a frozen guard's decision layer."

3 条 anchor 事实（不 tuning）：
1. clipping-only benign FPR: 67.5% → 76.0%
2. LOBTO PG-full: [Day 12 填]
3. Certificate 4/5 seeds valid: [Day 12 填]

停损条件（任一触发即撤退）：
- Day 12 EOD: PG-full FPR >= backbone
- Day 15 EOD: <4/5 seeds certificate valid
- Day 21 EOD: <2 backbones 复现 mechanism
```

---

**Advisor signature:** AI research-copilot (advisor mode)
**Plan version:** v1.0 (2026-07-12)
**Next review:** Day 15 EOD (Gate γ verdict)
**Escalation contact:** 用户与合作组导师
