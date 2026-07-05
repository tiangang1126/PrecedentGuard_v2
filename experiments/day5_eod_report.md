# Day 5 EOD Report — Week 2 起点

**Date:** 2026-07-05 EOD (Sprint Day 5)
**Sprint status:** Gate α PASSED (Day 4 EOD); Week 2 controlled interventions upcoming

---

## 一、Day 5 交付总览

| 时段 | 任务 | 状态 | 关键证据 |
|---|---|---|---|
| A.M. 紧急 | 恢复 `precedentguard` 包 importability（外部 __init__.py 声明新契约）| ✅ | `import precedentguard` OK；tests 89→130 |
| A.M. | 实现 `backends/` 包（3 vendor：Llama-Guard / ShieldGemma / Granite-Guardian）| ✅ | `HFGuardBackend` 抽象 + 3 具体子类，lazy loading + injectable score_fn |
| A.M. | 实现 `retrieval.py`（`PrecedentCapsule` + `SimplePrecedentStore`）| ✅ | 论文 §4.3 全实现 + water-fill w_max cap |
| P.M. | 修 B4（A5 扩展到 α + external timestamp disclosure）| ✅ | certificate.py 4 处更新 + 主稿 §5.1/§5.4 |
| P.M. | 修 B5（η adversarial vs average 澄清）| ✅ | 主稿 §5.5 双 η 定义 + 警告段 |
| P.M. | 集成 precedent 到 `PrecedentGuard.decide()` | ✅ | 完整 5 阶段流水线打通；7 集成测试全绿 |

**Tests 89 → 139（+50）全绿；smoke test 5/5 BLOCK + 5/5 ALLOW + n=100 非空证书 U=0.1358 保持。**

---

## 二、AI 冷读审稿 7 条 BLOCKER 消灭进度

| # | 内容 | 状态 |
|---|---|---|
| B1 | Corollary 1 DPI 方向 + LaTeX typo + Prop 1 max-of-two | ✅ Day 4 消灭 |
| B2 | Operator 承诺（4→2）窄化 | ✅ Day 4 消灭 |
| B3 | Prop 1 measurability preamble | ✅ Day 4 消灭 |
| B4 | A5 只封锁 Γ 未封锁 α；registry 只是 self-attestation | ✅ **Day 5 消灭** |
| B5 | A4 vs §5.5 η 补丁——adversarial vs average η 非可交换 | ✅ **Day 5 消灭** |
| B7 | `guard.py` 缺 precedent retrieval | ✅ **Day 5 消灭** |
| **B6** | **§7 全章占位，真实端到端实验缺失** | ⏳ **Day 6-10 sweep** |

**7 条 BLOCKER 中 6 条已消灭。仅剩 B6（实验）为 Week 2 主任务。**

---

## 三、当前项目全景

```
PrecedentGuard_pro2/
├── precedentguard/                     [8 modules, ~1900 LOC]
│   ├── __init__.py                    (external-declared API contract)
│   ├── types.py                       (+ NodeType.PRECEDENT)
│   ├── eig.py
│   ├── counterfactual.py              (+ precedent_counterfactual_delta;
│   │                                    GuardInterface accepts precedents)
│   ├── clipping.py
│   ├── guard.py                       (+ precedent_store integration,
│   │                                    5-stage full pipeline)
│   ├── certificate.py                 (+ alpha_grid A5-extended enforcement)
│   ├── retrieval.py  [NEW]            (PrecedentCapsule + Store + water-fill)
│   └── backends/  [NEW]
│       ├── __init__.py
│       ├── base.py                    (HFGuardBackend abstract base)
│       ├── llamaguard.py
│       ├── shieldgemma.py
│       └── granite.py
├── tests/                              [7 test files, 139 tests, 100% PASS]
│   ├── test_eig.py                    (21)
│   ├── test_counterfactual.py         (14)
│   ├── test_clipping.py               (28)
│   ├── test_guard.py                  (8)
│   ├── test_certificate.py            (20; +2 A5-extended)
│   ├── test_backends.py               (15)
│   ├── test_retrieval.py              (26)
│   └── test_guard_with_precedents.py  (7)  [NEW]
├── scripts/
├── experiments/
│   ├── gate_alpha_report.md
│   ├── gate_alpha_review_ai_20260704.md
│   ├── day3_smoke.log
│   └── day5_eod_report.md              [THIS FILE]
├── configs/
└── [paper artifacts]
    ├── PrecedentGuard_AAAI27_Revised_Draft_v0.2.md
    │   (+ §5.1 A5 扩展; §5.4 external anchor remark; §5.5 双 η 定义)
    └── precedentguard_theorems_v0.2_skeleton.tex
```

---

## 四、关键技术决策记录

### D1. Precedent 类型化（新增 `NodeType.PRECEDENT`）
- 论文 §4.6 公式 $S_{PG} = B + \text{clip}(\Sigma_e \beta_e \tilde\delta_e^{PG} + \Sigma_i w_i \tilde\delta_i^{PG})$ 明确区分 evidence 与 precedent 贡献
- 实现选择：让 precedent 走同一 `Contribution + aggregate` 基础设施，但用独立 `NodeType.PRECEDENT` 作为 caps 键，`w_i` 作为 β 系数
- 好处：directional trust rule / type-cap 全部复用；坏处：precedent 的 caps 需要单独配置（在 `caps_by_type` 中显式列出，缺失时 raise）

### D2. GuardInterface 协议扩展 `precedents=None` 参数
- 现有 mock guards 全部加 `precedents=None` 参数（3 处更新，测试全绿）
- HF 后端（Llama-Guard/ShieldGemma/Granite）prompt 加 precedent 段，vendor-specific 格式
- 反事实模式：precedent counterfactual = 从 retrieved list 中 ablate 单个 capsule；evidence counterfactual 现在也传 precedents 保持 constant

### D3. A5 扩展到 α 网格（`alpha_grid` 参数）
- `grid_hash` / `commit_grid_hash` / `assert_grid_committed` / `certify` 均新增 `alpha_grid: Optional[list[float]]`
- 向后兼容：`alpha_grid=None` 时行为不变（legacy tests 全绿）
- 新兼容：显式 `alpha_grid=[...]` 时，α 必须属于承诺集，否则 raise `ValueError` 或 `RuntimeError`
- **诚实披露：** 主稿 §5.4 新增 remark 明说 local CSV registry 是 honest-author baseline；对抗可验证 pre-commitment 需要 RFC 3161 / OpenTimestamps / 公开 git tag

### D4. Water-fill w_max 上限算法
- 首次实现（简单 cap + renormalize）在"单一 capsule 主导，其余为零"边界情况下 broken（cap 后重归一化把主导权重弹回 1.0）
- 改用 water-fill：主导降到 w_max，excess 均匀分配给剩余 capsule
- 单元测试覆盖此边界（`test_w_max_cap_enforced`）

---

## 五、Week 2 起点 — Day 6 计划

**目标（B6 消灭进入 §7 实证）：** 3 backbones × 3 suites × 3 attack budgets × 3 seeds sweep

> **实现状态说明：** 本节以下列出的 `experiment_plan_v1.yaml`、`gen_controlled_intervention_suite.py`、`agentdojo.py`、`registry.csv`、`certificate_grid.yaml` 是 **Day 6 待落地交付物**，不是当前工作区里已经存在的文件。执行前必须先检查文件是否已创建，避免按计划文档误触发不存在的脚本。

### Day 6（明日）子任务

1. **09:00-11:00 — 实验蓝图 v1.0 落地**
   - 冻结 `configs/experiment_plan_v1.yaml`：backbones = {Llama-Guard-3-1B, ShieldGemma-2B, Granite-Guardian-3.2-2b}，suites = {AgentHarm subset, AgentDojo full, AgentPoison memory subset}
   - 生成受控 intervention suite（1000 paired，合成）——脚本 `scripts/gen_controlled_intervention_suite.py`
   - A5 grid hash commit：`configs/certificate_grid.yaml` + `experiments/registry.csv` 首行

2. **11:00-14:00 — 数据管线打通**
   - 从 AgentDojo/AgentHarm 的 execution trace 抽取 EIG（`precedentguard/data_pipelines/agentdojo.py`）
   - 从 AgentPoison trace 抽取 memory poisoning 场景 EIG
   - 每个 suite 首次 100-example smoke on real backbone（3090 Ti FP16）

3. **14:00-18:00 — 首次 backbone sweep**
   - Suite A + Suite B on Llama-Guard-3-1B（首个 backbone），全部 attack budget 网格
   - 结果 → `experiments/day6_sweep_llamaguard_suite_ab.log`
   - 计算 §7.1 主表格第一行数字（backbone-averaged 尚需 Day 7）

### Day 7-10 sweep（B6 主体）

| Day | Suite | Backbone(s) | 计算量估算 |
|---|---|---|---|
| Day 7 | A+B | ShieldGemma-2B | 8h 3090 Ti |
| Day 8 | A+B | Granite-Guardian | 8h 3090 Ti |
| Day 9 | C（memory poisoning）| 全 3 backbone | 12h 3090 Ti |
| Day 10 | Adaptive attack + Cross-domain | 全 3 backbone | 8h 3090 Ti |
| Day 11 EOD | **Gate β 判定** | — | — |

**Gate β 通过标准：**
- 8+ baselines 出数
- 证书在 dev set 上 ≥4/5 seeds 有效（empirical FNR/FPR ≤ U_FN/U_FP）
- §7.1 主表格 v0.5（backbone-averaged）落地

---

## 六、导师红线（Day 6-10 必须遵守）

1. **A5 grid hash 必须在生成 calibration split 之前 commit**——脚本自检；违反直接 abort
2. **每次 backbone sweep 前先跑 10-example smoke on real backbone**——防止 3090 Ti OOM / model_id 拼写错 / cache 路径错
3. **`experiments/registry.csv` 每一行都要有真实时间戳和 hash**——不允许手动编辑；不允许追溯改行
4. **每个 backbone × suite 组合的 `.log` 完整保留**——即使 sweep 中途崩溃，也要保存已跑完的部分
5. **不允许 vibrant 掉 baseline**——如果某个 baseline（例如 SMSR/MemLineage/AttriGuard/AgentSentry）跑不出来，明确记录 blocker 并在 §6.5 明说；不允许改成"can be compared where..."（R4 已警告避战）

---

## Response（按 CLAUDE.md §18）

**Decision:** Day 5 P.M. 计划完全落地，6 条 AI-review BLOCKER 消灭（B1/B2/B3 in Day 4；B4/B5/B7 in Day 5）；仅剩 B6（实验）为 Day 6-10 主任务。

**Evidence:** 
- Tests: 89 → 139 (+50)，全绿，0.036s 完成
- Smoke test 未回归：5/5 BLOCK + 5/5 ALLOW + n=100 非空 U=0.1358
- 论文修改：§5.1 A5、§5.4 external anchor remark、§5.5 双 η + 警告，全部 markdown 语法正确
- 代码：8 modules、~1900 LOC、full pipeline 打通 (§4.1→§4.8 Algorithm 1)

**Files changed:** 
- 新建：`precedentguard/backends/{base,llamaguard,shieldgemma,granite,__init__}.py`, `precedentguard/retrieval.py`, `tests/test_backends.py`, `tests/test_retrieval.py`, `tests/test_guard_with_precedents.py`, `experiments/day5_eod_report.md`
- 修改：`precedentguard/{types,counterfactual,guard,certificate}.py`, 主稿 §5.1/§5.4/§5.5, 3 处 mock guard 更新

**Validation performed:** 139/139 unit tests pass; day3 smoke rerun no regression; A5-extended α locking 双重校验（`test_a5_extended_alpha_grid_locking` + `test_a5_extended_certify_rejects_out_of_grid_alpha`）; water-fill w_max cap 边界测试

**Risks / limitations:** 
(a) HF backend 的 chat template 基于公开文档推测，Day 6 首次 real backbone smoke 需要 spot-check 与官方 chat template 一致性；
(b) `SimplePrecedentStore` 未持久化，Day 8+ corpus 增大后需要考虑替换为 FAISS/Chroma；
(c) 实验蓝图仍需明日冻结（Task #24）—— backbone / suite / attack budget / seed 数量的最终版本；
(d) 3090 Ti 独占性未确认——Day 6-10 计划假设 GPU 全时可用，若被其他任务抢占需要收缩计划

**Next highest-value action:** Day 6 09:00——冻结 `configs/experiment_plan_v1.yaml` 并 commit 首个 grid hash 到 registry；开始 AgentHarm/AgentDojo 数据管线搭建。**今晚可以合上电脑。**
