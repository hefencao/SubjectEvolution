# Subject Evolution v0.29

一个以**可审计世界状态、局部交互、遗传策略、动态知识副本和候选主体结构**为核心的演化模拟参考实现。

科学核心不引入第二套“生物型危险实体”。环境层只包含资源、权威危险场、死亡痕迹及默认关闭的低耦合标量场插件；具有出生、死亡、策略、关系、记忆或谱系的危险主体，应由现有实体系统分化，而不是在环境模块中复制。

## v0.29 重点

v0.29 不修改默认世界动力学。它审计了三批 v0.28 event-timed 结果并将此前隐含的三类测量规则提升为版本化协议：

- 三批结果完整覆盖 18 anchors × 6 eligible interventions，即 **108/108 pairs**；共同 event state 的 alive、全局 stable-ID 和区域 stable-ID 配对全部通过；
- `group label` 明确为 `trusted-directed-fixed-round-min-label-v1`，传播轮数、信任阈值和最小成员数进入配置、manifest 与运行 provenance；
- 局部区域明确为 `normalized-fixed-count-grid-v1`，发布归一化拓扑、物理区域尺寸、每区世界格数量和 partition SHA-256；
- anchor planner 升级为 `exposure-only-local-peak-selection-v2`，发布候选排名、区域边界和 partition hash，并默认拒绝静默混合不同物理区域几何；
- 长跑分析升级为 `multi-seed-long-run-analysis-v8`；
- 新增 `subject_evolution.protocol_audit`，可从配置和 manifest 直接生成 group/region/anchor 协议审计；
- `pyproject.toml` 的 build-system 现在可显式依赖 `wheel`。

## 当前 group label 策略

当前群组不是精确无向连通分量，也不是主体存在判定，而是高信任有向关系上的有限轮次候选分组：

1. 每个活实体以自己的**物理槽位索引**初始化标签；
2. 关系槽只有在目标仍存活且物化后的 trust ≥ `trust_group_threshold` 时形成可传播的有向边；
3. 每一轮，实体将自己的标签更新为“当前标签与所有可达出边目标标签中的最小值”；
4. 固定执行 `group_label_propagation_rounds` 轮；
5. 同一传播根的成员数达到 `group_min_members` 才形成群组；群组 token 使用该根槽位上实体的 stable entity ID，否则 token 为 0；
6. 群组标签按独立的 refresh 策略重算。旗舰配置使用 `adaptive-topology-v1`：最短 100 ticks、最长 300 ticks，由初始快照、关系拓扑变脏、预测 trust 衰减跨阈值或最大陈旧期触发。

旗舰配置：阈值 `0.12`、传播 `8` 轮、最少 `6` 个成员。成功分享产生正向完整 trust 增益和反向半增益，因此阈值化后的边仍可能具有方向性。

## 不同地图大小下的区域策略

当前局部诊断使用 `normalized-fixed-count-grid-v1`：

- 区域数由 `spatial_stress_regions_x × spatial_stress_regions_y` 固定；旗舰配置为 `4 × 4`；
- 世界坐标先归一化到 `[0,1) × [0,1)`，再按等宽等高矩形划分；
- `region_id = region_y * regions_x + region_x`，即先 y 后 x 的行主序；
- 边界采用半开区间，最外侧做裁剪。

因此，保持 `4 × 4` 而放大地图时，**归一化拓扑不变，但每个区域的物理宽高和面积会变大**；改变物理世界网格分辨率时，每个区域代表的 world-cell 数也会变化。旗舰 `128 × 128` 地图、`32 × 32` 世界格下，每区为 `32 × 32` 物理单位和 `8 × 8` 世界格。

v0.29 同时发布 topology hash 与包含物理几何的 partition hash。跨地图 manifest 默认要求物理区域几何、世界格覆盖和拓扑一致；确需混合时必须显式使用 `--allow-mixed-region-partitions`，并承担尺度不可比的解释责任。

## Anchor 的确定方式

默认 anchor selection 为 `exposure-only-local-peak-selection-v2`，对每个 seed、事件类型和区域分别执行：

1. 只读取 tick、区域 alive、对应 exposure（scarcity/crowding/mortality）和 checkpoint 可用性；不读取凝聚度、文化根、传播流、谱系或动作结果；
2. 丢弃非有限 exposure、区域 alive 小于阈值的记录；每条区域序列至少需要 5 个有效窗口且标准差非零；
3. 计算该区域自身时间序列的分位阈值，默认 80%；
4. 候选必须是不低于前一窗口、严格高于后一窗口的内部局部峰；
5. 同一区域内按默认 2 个窗口的最小间隔去重；
6. 用该区域自身均值和标准差计算 z-score，并按 z-score 降序、tick 升序、region ID 升序排序；
7. 优先选择不同区域，达到每 seed、每事件类型默认 2 个 anchors；候选区域不足时才允许同一区域重复；
8. 为每个事件选择严格早于 event tick 的最新完整 checkpoint，默认 post-event horizon 为 120 ticks。

z-score 只用于同一事件类型内部排序，不能把 scarcity、crowding 和 mortality 的 z-score 当作同一强度量尺。自然峰值也不是随机 exposure，因此 paired branch 只识别共同事件状态形成后的短期机制效应，不证明 exposure 本身的因果作用。

## 安装

```bash
python -m venv .venv
source .venv/bin/activate            # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e .
```

CPU 参考实现只需要 NumPy。GPU 路径需要与本机 CUDA 主版本匹配的 CuPy；CUDA 12 和 CUDA 13 的 CuPy 包不能同时安装。

## 快速运行

```bash
python -m subject_evolution.cli \
  --config configs/smoke_cpu.json \
  --output runs/smoke_cpu \
  --backend cpu
```

旗舰科学长跑配置：

```bash
python -m subject_evolution.multi_seed \
  --config configs/mvp_short_latent_l2_memory_topk_inherited_heterogeneous_budget_matched_costed_transfer_mortality_trace_adaptive_groups_longrun.json \
  --seeds 10001,10002,10003 \
  --output runs/mortality_trace_adaptive_groups_multiseed \
  --backend gpu \
  --until-tick 1500
```

该配置使用 `gpu_semantics_mode="strict-reference"`。请求 GPU 时会验证设备，但世界语义仍由 CPU reference 路径权威执行；真实 `hybrid-accelerated` 多 tick parity 尚未证明，不能作为科学基线。

## 协议审计

```bash
python -m subject_evolution.protocol_audit \
  --config configs/mvp_short_latent_l2_memory_topk_inherited_heterogeneous_budget_matched_costed_transfer_mortality_trace_adaptive_groups_longrun.json \
  --manifest analyses/natural_event_matrix/natural_event_matrix_manifest.json \
  --output analyses/protocol_audit
```

输出同时给出 group label、group refresh、空间区域和 anchor selection 的 schema、参数、哈希及解释边界。

## 自然事件实验工作流

```bash
python -m subject_evolution.natural_event_matrix \
  --run-root runs/mortality_trace_adaptive_groups_multiseed \
  --analysis-json analyses/mortality_trace_adaptive_groups/long_run_analysis.json \
  --event-kinds scarcity,crowding,mortality \
  --event-quantile 0.80 \
  --events-per-kind 2 \
  --horizon 120 \
  --output analyses/natural_event_matrix
```

推荐使用 event-timed execution：

```bash
python -m subject_evolution.natural_event_timed_execution \
  --manifest analyses/natural_event_matrix/natural_event_matrix_manifest.json \
  --event-kinds crowding,mortality,scarcity \
  --interventions disable-knowledge-transfer,freeze-group-refresh,neutralize-resource-affinity \
  --output analyses/event_timed_primary

python -m subject_evolution.natural_event_timed_execution \
  --execution-plan analyses/event_timed_primary/natural_event_timed_execution_plan.json \
  --output analyses/event_timed_primary \
  --execute \
  --backend gpu \
  --gpu-semantics-mode strict-reference
```

每个 pair 都必须证明 event alive、全局 stable-ID hash 和区域 stable-ID hash 相同。旧 `natural_event_execution` 保留为 `checkpoint-immediate-v1` 总效应估计量，不与 `anchor-event-tick-v1` 结果池化。

## 核心能力

- 2D 周期世界、四类不可完全替代资源、异步多生态位季节变化；
- 固定容量 SoA 实体、出生/死亡计划、谱系继承与稀疏突变；
- 可遗传 8-action × 16-feature 策略矩阵；
- K1–K4 动态知识副本、局部后果更新、有代价传播、内容根谱系与候选图；
- L1/L2 可变长度潜知识、量化 MLP residual、路由计算成本；
- 量化工作记忆与遗传 Top-k 临时选择器；
- 固定预算四资源亲和、死亡痕迹观察、adaptive group refresh；
- CPU reference、GPU strict-reference 和实验性 hybrid-accelerated 路径；
- checkpoint、共同前史、event-timed pairing、共同边界与 stable-ID cohort；
- 版本化 group label、空间区域、anchor selection 与协议审计。

## 文档

- [当前项目状态](docs/PROJECT_STATUS.md)
- [科学问题与研究债务](docs/SCIENTIFIC_ISSUES.md)
- [变更记录](docs/CHANGELOG.md)
- [架构与提交边界](docs/ARCHITECTURE.md)
- [v0.29 文档](docs/v0.29/README.md)

发行压缩包不包含 `docs/archive`。更早的完整历史仍保存在旧版本发行包中。
