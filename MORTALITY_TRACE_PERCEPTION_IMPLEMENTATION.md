# v0.21 局部死亡痕迹感知实现

## 目标

旧环境中，资源稀缺直接进入观察与采集结算，而死亡只是延迟后的世界事件。实体没有可用的局部死亡证据，因此不能通过遗传、工作记忆或知识路由学习“某位置曾发生死亡”与后续结果之间的关系。

v0.21 新增可关闭 schema：

```text
local-decaying-mortality-trace-v1
```

死亡提交时，只在死亡发生的物理格点沉积无身份、无谱系、无群组信息的局部痕迹。痕迹随后衰减并向周期世界的四邻域扩散。

## 环境状态

```text
mortality_trace[grid_y, grid_x] float32
```

配置：

- `mortality_trace_decay`
- `mortality_trace_diffusion`
- `mortality_trace_deposit`
- `mortality_trace_max`
- `mortality_trace_observation_weight`

正式长跑配置使用：衰减 `0.04`、扩散 `0.08`、每次沉积 `0.25`、上限 `2.0`、观察权重 `0.6`。

## 感知边界

痕迹只合并到公开 danger observation：

```text
public_danger = base_hazard + observation_weight × mortality_trace
```

它影响：

- danger signal；
- danger gradient；
- 知识上下文中的危险通道；
- 继而允许遗传策略、工作记忆和局部知识学习其意义。

它不影响：

- 物理 hazard 对 integrity 的直接伤害；
- 能量或繁殖奖励；
- 行动强制替换；
- 群组或谱系分类；
- 全局死亡计数。

因此“死亡痕迹”是一个可学习的环境证据，不是全知死亡标签或预设避让控制器。

## CPU/GPU 与持久化

- NumPy `Environment` 和 `DeviceEnvironment` 使用同一衰减、扩散、沉积和裁剪语义；
- hybrid runtime 会同步该场；
- 完整 `.sechk`、clone 和 replay 保存痕迹；
- v0.20 checkpoint 缺少该场时恢复为零场；
- metrics 和 `evolution_progress.jsonl` 记录 mean/std/max。

## 当前边界

- 所有实体共享同一公开痕迹场，尚未加入遗传性痕迹敏感度；
- 痕迹本身没有独立感知成本；
- 120-tick 对照只证明痕迹进入策略轨迹，不能证明长期适应优势；
- 真实 CUDA hybrid 多 tick parity 尚未验证。
