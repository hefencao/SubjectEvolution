# 架构与提交边界

## 世界循环

```text
配置与版本化 schema
        ↓
环境 / 信息场 / 空间索引 / 社会关系快照
        ↓
只读 observation plan
        ↓
遗传策略 + 动态知识 residual + 工作记忆 + Top-k
        ↓
control proposal → arbitration → action intent
        ↓
只读 conflict resolution plan
        ↓
受控 commit
        ↓
实体 / 环境 / 信息 / 关系 / 生命周期 / 知识 / 主体图更新
        ↓
metrics / logs / checkpoint / offline analysis
```

策略、知识路由、控制器和冲突解析器不得直接写世界。只有消费已版本化计划的提交器可以修改权威状态；提交器可位于 CPU、GPU 或未来的分布式分区，不在架构上永久绑定硬件。

## 权威状态

- CPU reference：所有世界状态由 CPU 语义权威执行。
- GPU strict-reference：验证 GPU/CuPy 可用性，但继续执行 CPU reference 世界，适合当前科学运行。
- GPU hybrid-accelerated：环境/信息场、空间、观察、策略与部分冲突计划可在设备上执行；关系、生命周期、主体图及多项日志仍由 CPU 提交。该路径尚无长程多 tick parity 证明。

## 环境边界

科学核心包含四资源、季节、权威危险场和实体死亡形成的局部死亡痕迹。`additive-environment-field-process-v1` 只允许插件返回有限、非负、同网格形状的标量增量；插件不能读取实体、关系、群组、谱系、策略、知识、记忆或生命周期。

旧 moving Gaussian source 是默认关闭的兼容/娱乐扩展，不属于科学生态基线。具有生命周期和策略的危险主体必须复用现有实体系统。

## 知识层

知识内容、承载副本与承载主体分离。传播需要伙伴机会、注意力、发送/接收能量和容量；本地结果更新副本置信与 outcome 统计。策略只读取经置信、样本、Top-k、工作记忆和计算预算约束后的 residual。

候选知识主体图是诊断结构，不是本体论判定，也不拥有额外世界写权限。

## Group-label protocol

群组标签规划与刷新调度是两个独立协议层。

### Label planner

`trusted-directed-fixed-round-min-label-v1` 的输入是只读 `GroupDetectionSnapshot`：alive mask、每个拥有者的固定关系槽、物化 trust、stable entity IDs 和配置参数。

```text
label_i^0 = physical slot i

for round = 1..R:
    label_i^round = min(label_i^(round-1),
                        labels of eligible outgoing targets)
```

eligible edge 需满足目标 alive 且 trust ≥ threshold。实现使用上一轮标签的快照进行同步更新。传播结束后按最终根统计成员数；不足 minimum members 的根映射为 token 0，其余根的 token 是根槽位上实体的 stable ID。

成功分享的 relation plan 写入正向完整 trust gain 和反向半 gain。边在历史、衰减和阈值化后仍可能是单向，因此该 planner 是有限轮、有向的近似候选结构，不等于无向图精确连通分量。

### Refresh scheduler

`adaptive-topology-v1` 不在每 tick 重算标签。旗舰配置：minimum period 100、maximum period 300；初始快照、最短期后 topology dirty、预测 trust 衰减跨阈值或最大陈旧期触发更新。`freeze-group-refresh` 只冻结该调度后的刷新，不改变已有关系、死亡清理或世界提交。

任何 rounds、threshold、minimum members、edge semantics 或 refresh semantics 的改变都必须产生新配置 provenance；不能将离线替代分组静默写回世界。

## Spatial-region protocol

`normalized-fixed-count-grid-v1` 是 local-stress、event cohort 和 natural-event planner 共享的唯一当前 region mapping：

```text
u = (x mod world_width) / world_width
v = (y mod world_height) / world_height
rx = clip(floor(u * regions_x))
ry = clip(floor(v * regions_y))
region_id = ry * regions_x + rx
```

矩形边界半开，最外层裁剪；世界本身仍是周期边界。该划分不反馈世界，只用于诊断和实验定位。

固定 region count 意味着 normalized topology 随地图尺寸保持一致，但 physical region width/height 随世界物理大小缩放；world cells per region 随物理网格分辨率变化。v0.29 分离：

- topology SHA：schema、regions_x/y、mapping、boundary convention；
- partition SHA：再包含世界物理大小、world-grid 分辨率和派生物理尺度。

跨 run anchor planning 默认要求 topology 和物理 partition 一致。显式允许 mixed partitions 只解除执行阻止，不使指标自动可比。

## Anchor-selection protocol

`exposure-only-local-peak-selection-v2` 是离线规划器，不读取 post-event outcome。

对每个 run、event kind、region：

1. 建立 exposure 时间序列并应用 tick、finite、minimum alive 过滤；
2. 至少 5 个有效窗口且标准差非零；
3. 使用该区域自身 quantile 阈值；
4. 保留 interior local maxima，规则为 value ≥ previous 且 value > next；
5. 在同一区域内执行 minimum-gap windows；
6. 计算该区域自身 mean/std 下的 z-score；
7. 全部候选按 z-score 降序、tick 升序、region ID 升序；
8. 先从不同 region 选取，候选 region 不足时才复用；
9. 选择 checkpoint_tick < event_tick 的最新完整 checkpoint。

candidate rank、selection rank、region bounds 和 partition SHA 进入 v2 manifest。z-score 只用于同一种 exposure 的排序，不是跨事件或跨 partition 的强度单位。analysis summary 可以进入 rationale/audit，但 `used_for_anchor_selection=false`。

## 反事实与 event-timed 边界

科学干预通过注册表声明 kind、target scope 和是否直接控制行动。直接行动替换只允许 entertainment 模式。

推荐 event-timed 执行：

```text
signed source checkpoint
        ↓ shared deterministic prefix
nominal event checkpoint (file/state SHA-256)
        ├─ capture common boundary + stable-ID cohort → baseline
        ├─ capture same boundary + cohort → intervention A
        └─ capture same boundary + cohort → intervention B
```

干预只在 event checkpoint 加载后应用。pairing audit 要求 baseline/intervention 的 event alive、global identity hash、regional identity hash 全部一致。checkpoint-immediate 估计量继续存在，但禁止与 event-timed 结果池化。

## Common-boundary 与 cohort 诊断

checkpoint-common boundary 以 stable entity ID 冻结群组 token，只对已提交分享流进行第二套分类，不参与世界行动或群组更新。它用于拆分真实流变化与 current-label 定义变化。

Event cohort 将终点区域人口拆为 retained、survived outside、absent、existing in-migrants 和 post-event born，并验证恒等式 residual=0。它是 endpoint identity accounting，不是 pathwise migration/death ledger。

## Cross-result synthesis boundary

`natural_event_result_synthesis` 要求输入绑定同一 manifest hash，以 anchor/intervention identity 去重，拒绝核心世界结果冲突，并重新执行 seed-first aggregation。它不能修改 manifest、补造结果、将自然事件变成随机实验，或从机制近端指标推出人口与主体性结论。
