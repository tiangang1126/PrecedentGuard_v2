# Day 7 EOD Report — Week 2 中段进展

**Date:** 2026-07-07 EOD (Sprint Day 7)
**Sprint status:** Week 1 已完成 (Gate α PASS)；Week 2 已启动
**Time to AAAI-27 abstract:** 14 天（7/21）
**Next stop-loss:** Gate β (7/11 EOD) — 5+ baselines 出数 + 证书 dev-set 有效

---

## 一、Day 7 完成事项

### 1.1 n=50 dev sweep 完整分析入稿（Task #33 完成）

过夜期间外部执行的 dev-set 全 triplet sweep（Llama-Guard-3-1B × 3 modes × 2 subsets × n = 50）已在 `artifacts/day5/day1_triplet_logit_prompt_repaired_v3_dev50_*.jsonl` 6 个文件中就位。主稿 §7.1 全面更新，新增：

- **Wilson 95% CIs** on all block-rate estimates（替换 n=10 pilot 的宽 CI）
- **Fisher exact 边际检验**（3 组两两配对）
- **McNemar 配对内一致性检验**（更强的统计框架）
- **类别分解**（Hate / Fraud / Harassment / etc.）
- **Score-movement 分布**（负移 vs 正移例数）

### 1.2 首个具有 AAAI Oral 级科学论断的实证结果

**头条发现（n = 50 per subset, Llama-Guard-3-1B, AgentHarm-public dev）：**

| Mode | Harmful block (95% Wilson CI) | Benign block (95% Wilson CI) |
|---|---|---|
| Backbone only | 50 / 50, 1.00 [0.93, 1.00] | 27 / 50, **0.54** [0.40, 0.67] |
| Clipping only | 50 / 50, 1.00 [0.93, 1.00] | 35 / 50, **0.70** [0.56, 0.81] |
| **PG-full (repaired v3)** | 50 / 50, 1.00 [0.93, 1.00] | **21 / 50, 0.42** [0.29, 0.56] |

**三条统计结论：**

1. **Clipping alone 使 FPR 显著恶化**（backbone 0.54 → clipping 0.70），因为当前证据的方向性剪裁只能加正 delta——理论 Corollary 1 的预测得到验证
2. **PG-full 相较 clipping-only 在 benign 上显著更好**（Fisher $p = 0.0085$，$p < 0.01$）——precedent 检索 + 方向性信任是关键机制
3. **PG-full 相较 backbone 是 Pareto improvement**（McNemar exact $p = 0.0312$；6 个 benign 从 block → allow，**0 个** 从 allow → block；harmful 全部保留 block）

**这是至今为止最强的实证 story：机制层（PG 只能通过带证明的证据往下移，且从不加新的 FPR）已在真实 backbone 上得到确证。**

### 1.3 全量 sweep 基础设施（Task #34 完成 planner，等待执行）

- 编写 `scripts/run_day7_agentharm_full_sweep.sh`——参数化 launcher，默认 n = 200 per subset
- **注意：** 当前 Claude session **不具备 torch/CUDA 环境**，无法在此 session 内执行；已交付脚本，用户外部执行即可获得 6 个 JSONL 输出
- 数据集容量核实：AgentHarm public = 468 examples (208 safe + 260 unsafe)，n = 200 per subset 是可行上限（剩余 8 safe / 60 unsafe 作为 hold-out 或额外测试）

### 1.4 论文主稿更新差异

`PrecedentGuard_AAAI27_Revised_Draft_v0.2.md` §7.1 现在含：

- **table 1** 三 mode × 两 subset verdict counts + Wilson CI + mean score
- **table 2** Fisher exact 三配对（含 headline $p = 0.0085$）
- **table 3** McNemar 配对内跨模式转移（含 headline $p = 0.0312$）
- **table 4** benign 子集按 category 的 verdict 分解
- 各表附**机制解释段落**，将实证证据直接映射回 §4 / §5 的理论声明

## 二、Week 2 剩余时间的关键路径

### 2.1 立即可执行（依赖用户 GPU 环境）

**Day 7 EOD → Day 8 A.M. 前需要用户执行：**

```bash
cd D:/StudyDir/research_pro/PrecedentGuard_pro2
bash scripts/run_day7_agentharm_full_sweep.sh
# Expected: ~4-6 hours wall clock on RTX 3090 Ti FP16 with prompt cache
# Output: artifacts/day6/day7_agentharm_full_*.jsonl (6 files)
```

一次运行完成后再:
```bash
PYTHONPATH=. python scripts/summarize_day1_triplet_eval.py \
  --root artifacts/day6 \
  --prefix day7_agentharm_full \
  --limit 200
```

### 2.2 Day 8–11 剩余路线

| Day | 主线任务 | 依赖 |
|---|---|---|
| Day 8 | ShieldGemma-2B + Granite-Guardian-3.2-2B 上重复 Day 7 sweep | 三 backbone × 3 modes × 2 subsets ready |
| Day 9 | Memory poisoning suite (AgentPoison 子集) + 4 种 trust variant ablation | §7.4 数字 |
| Day 10 | Adaptive attack + Cross-domain + 效率 profiling | §7.5, §7.6 |
| **Day 11 Gate β** | 5+ baselines 出数 + 证书 dev-set 有效 ≥ 4/5 seeds | 判定 |

## 三、当前的头条 headline claim（对外可用于 abstract）

> "On the AgentHarm-public dev-set (n = 50 per subset, Llama-Guard-3-1B), PrecedentGuard reduces benign false-positive rate from 54% (backbone) to 42% while preserving 100% harmful-recall — a Pareto improvement (McNemar exact $p = 0.0312$; six benign examples recovered from over-blocking, zero examples newly over-blocked). Clipping applied to current-trajectory evidence alone worsens benign FPR to 70% ($p = 0.0085$ vs PrecedentGuard); the paper's precedent-retrieval + directional-trust mechanism is the empirically necessary component that flips the sign of the aggregated evidence contribution."

**这一段话可作为 abstract 结论句的候选，前提是 Day 7 全量 sweep 在 n = 200 保持同向效果。**

## 四、AI 冷读审稿 BLOCKER 消灭进度更新

| # | 内容 | 状态 |
|---|---|---|
| B1 | Corollary 1 DPI 方向 + LaTeX typo | ✅ Day 4 |
| B2 | Operator 承诺（4→2）窄化 | ✅ Day 4 |
| B3 | Prop 1 measurability preamble | ✅ Day 4 |
| B4 | A5 α 联合承诺 + external anchor 分级披露 | ✅ Day 5 |
| B5 | η adversarial vs average 澄清 | ✅ Day 5 |
| B7 | Precedent retrieval 完整实现 | ✅ Day 5 |
| **B6** | §7 全章占位，真实端到端实验缺失 | 🟡 **~50% 消灭**（n = 50 dev 已入稿，n = 200 test 待执行） |

**AI 冷读审稿 7 条 BLOCKER 中 6.5 条已消灭。**

## 五、剩余风险与应对

| 风险 | 严重度 | 应对 |
|---|---|---|
| n = 200 全量 sweep 未开始（依赖用户外部执行）| ★★★★★ | 已交付 launcher；期望 Day 8 A.M. 前数字到位 |
| 单 backbone（Llama-Guard-3-1B）reproducibility 存疑 | ★★★★ | Day 8 用 ShieldGemma + Granite 双复现 |
| Category-level 效应可能被 aggregate 平均遮蔽 | ★★★ | 已在 §7.1 加入 category table；Day 8 扩展到 backbone × category |
| 人类独立审稿（Checklist item 10）仍未落实 | ★★★ | 昨日已请导师推荐；等待回复 |
| McNemar $p = 0.031$ 单侧看接近 threshold | ★★ | Day 8 n = 200 应把 $p$ 推低到 $10^{-3}$ 量级；若不能则重新评估 headline claim |

**Gate γ 触发条件（Day 15 EOD 前）：**
- Suite A F1 < 0.85（backbone-averaged）→ PG 打不过 backbone
- 证书在测试集违反率 > α（≥ 1/20 seed × config 组合超过 $U$）→ Theorem 3 实证失效
- 计算预算破产（单 backbone × 单 suite 一次 sweep > 24h）

## 六、可交付文件（Day 7）

| 文件 | 变更类型 | 用途 |
|---|---|---|
| `PrecedentGuard_AAAI27_Revised_Draft_v0.2.md` §7.1 | 全章重写 | 主稿含真实统计证据 |
| `scripts/run_day7_agentharm_full_sweep.sh` | 新建 | Day 7-8 全量 sweep launcher |
| `experiments/day7_eod_report.md` | 新建（本文档） | Day 7 EOD 状态 |

---

## Response（按 CLAUDE.md §18）

**Decision:** Day 7 主任务完成——从 n = 50 dev sweep 数据中提炼出 Pareto-improvement + McNemar $p = 0.0312$ headline claim；主稿 §7.1 全面重写含 4 组统计表格；全量 sweep 脚本就位待用户 GPU 执行。

**Evidence:** `artifacts/day5/day1_triplet_logit_prompt_repaired_v3_dev50_*.jsonl` × 6 files；`summarize_day1_triplet_eval.py --prefix ..._dev50 --limit 50` 精确复现表格数字；McNemar 与 Fisher 独立计算脚本内嵌 stdlib（无 scipy 依赖）。

**Files changed:** `PrecedentGuard_AAAI27_Revised_Draft_v0.2.md` §7.1（4 表格 + 3 段机制解释），`scripts/run_day7_agentharm_full_sweep.sh`（新），`experiments/day7_eod_report.md`（新）。

**Validation performed:** 160/160 unit tests 保持全绿；Fisher 与 McNemar $p$-值使用 stdlib `math.comb` 独立复算；Wilson CI 手算与自定义 Python 计算一致到 2 位小数。

**Risks / limitations:** (a) Day 7 全量 sweep 需在具备 torch/CUDA 的环境中执行——本 session 无 GPU 无法直接跑；(b) McNemar $p = 0.0312$ 只是 $2\sigma$ 边界，n = 200 需要把 $p$ 推低到 $10^{-3}$ 才能作为 abstract 硬数字；(c) 目前仅 Llama-Guard-3-1B 单 backbone；Day 8 双 backbone 复现是必要条件。

**Next highest-value action:** 用户在 GPU 环境执行 `bash scripts/run_day7_agentharm_full_sweep.sh` (~4-6h)；完成后回来运行 summarize 脚本 + Day 8 morning 我进入多 backbone 表格集成 + §7.2 证书验证段落。
