# 模拟演化工作路线图

## 原则

1. Python/CPU reference 先定义语义，GPU 负责加速而不重新定义模型。
2. 每个新机制必须说明状态、输入、代价、收益、随机性、提交顺序和可观察指标。
3. 先小规模可手工验证，再做数万/数十万实体性能优化。
4. 科学指标从模拟端产生；GUI 只显示，不成为实验真相来源。
5. 对演化结论使用多 seed、对照和 paired intervention，而不是单次视觉观察。

## 阶段 A：恢复真实源码与基线（P0）

**交付物**

- 实际 `src/subject_evolution/` split tree；
- 实际 `configs/` 和 tests；
- run manifest；
- CPU reference 配置；
- 当前 GPU 配置；
- `Simulation.step()` 阶段图。

**验收**

- 干净环境可运行；
- 同 seed CPU 重复结果一致；
- checkpoint 恢复与连续运行一致；
- 所有依赖和设备信息被记录。

## 阶段 B：不变量与预算闭合（P0）

**重点**

- ID/alive/free-pool；
- birth/death；
- resource/harvest；
- energy/integrity/fertility；
- share/benefit flow；
- social target 清理；
- group/subject graph 一致性。

**验收**

每一步都能生成预算摘要；debug 模式零越界、零非有限值、零重复提交。

## 阶段 C：CPU/GPU 语义对照（P0）

逐阶段比较 environment、information、policy、intent、resolution、commit、lifecycle、social/group 和 metrics。

**验收**

- 离散结果明确哪些必须完全一致；
- 浮点结果有阶段化容差；
- 首次偏差可定位；
- host/device 传输统计可解释。

## 阶段 D：生态基准（P1）

从无社会、无繁殖或固定策略场景开始，验证：

- 资源再生/扩散；
- 基础代谢和移动成本；
- 采集饱和与竞争；
- hazard 暴露；
- 承载力、崩溃和恢复；
- 周期边界。

**验收**

存在稳定、崩溃、恢复三类可重复参数区间，且机制解释明确。

## 阶段 E：演化有效性（P1）

建立最小可解释的 genotype→phenotype→behavior→fitness 链。

**指标**

- allele/trait frequency；
- selection differential；
- reproductive success；
- lineage survival；
- trait variance；
- effective population size；
- neutral/control divergence。

**验收**

预定义有利性状在选择环境中多 seed 稳定上升；中性或撤销选择压力时不出现同样结果。

## 阶段 F：社会与群体（P2）

在 Python 中明确：

- relation update；
- trust/familiarity 或其他社会变量；
- signal/message 的传输与影响；
- group detection、分裂、合并和 ID 持续性；
- 社会收益和资源收益边界。

**验收**

10–100 实体确定性场景可手工验证；打开社会机制后能用干预证明其因果影响。

## 阶段 G：大规模性能（P2）

在语义固定后进行：

- phase profiler；
- persistent device state；
- 稀疏 commit plan；
- 减少 host/device round-trip；
- segmented operations；
- 仅在必要时同步；
- 多种实体规模基准。

**验收**

性能提升不破坏 CPU reference 结果；每个优化都有前后 profile 和回归测试。

## 阶段 H：实验与回放（P2/P3）

- seed/parameter sweep；
- paired counterfactual；
- checkpoint/replay；
- 自动汇总与图表；
- 关键事件索引；
- GUI 仅按需要读取聚合指标或回放帧。

## GUI 冻结解除条件

只有满足以下之一才恢复 GUI 开发：

- 新模拟变量无法通过 metrics/日志/现有 Inspector 验证；
- 共享协议必须升级；
- 大规模运行中 GUI 已被 profiling 证明阻塞诊断；
- 回放或实验对比成为模拟验证的关键工具。
