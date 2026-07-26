# Group label、空间区域与 anchor 协议

## 1. Group label

Schema：`trusted-directed-fixed-round-min-label-v1`。

- 关系是拥有者→目标的有向固定槽；目标 alive 且 materialized trust 达阈值才 eligible。
- 初始 label 是物理 slot index。
- 每轮同步读取上一轮 label，取自身与 eligible outgoing target labels 的最小值。
- 固定 R 轮后按根计数，成员数不足 minimum members 的根保持未分组。
- group token 是根槽位上的 stable entity ID，不是 slot index。
- 成功分享写入 forward full gain、reciprocal half gain，因此 thresholded graph 可不对称。
- 旗舰参数：threshold=0.12、R=8、minimum members=6。

该算法只保证 R 跳内的有向最小标签传播，不保证大直径图完全收敛，也不等于无向弱连通分量。

Refresh 使用独立 `adaptive-topology-v1`：minimum 100、maximum 300 ticks；初始、dirty、预测阈值跨越或最大陈旧期触发。

## 2. 空间区域

Schema：`normalized-fixed-count-grid-v1`。

- 固定 `regions_x × regions_y`；
- 周期世界坐标先归一化；
- 等宽等高矩形；
- `region_id = ry * regions_x + rx`；
- half-open boundaries，外沿 clip。

旗舰：世界 128×128、world grid 32×32、region grid 4×4；每区 32×32 物理单位、8×8 world cells。

### 地图变化

| 变化 | normalized region ID topology | 物理区域大小 | 每区 world cells | 默认可池化 |
|---|---|---|---|---|
| 128→256，仍 4×4，grid 同比例放大 | 相同 | 变大 | 视 grid 而定 | 否，partition hash 不同 |
| 地图不变，32×32→64×64 grid | 相同 | 相同 | 变多 | 否，field resolution 不同 |
| 4×4→8×8 regions | 不同 | 变小 | 变少 | 否，topology hash 不同 |

v0.29 manifest 默认拒绝 mixed partition geometry；override 只允许执行，不自动赋予尺度可比性。

## 3. Anchor selection

Schema：`exposure-only-local-peak-selection-v2`。

每个 run/event/region 独立：

1. 过滤 finite exposure、tick 和 minimum region alive；
2. 有效窗口至少 5 且 std>0；
3. 区域自身 80% quantile 以上；
4. interior peak：`value >= previous and value > next`；
5. 同一区域 minimum gap=2 windows；
6. 区域自身 mean/std 的 z-score；
7. 排序：z 降序、tick 升序、region ID 升序；
8. 优先不同 region，达到每 kind/run 2 anchors；
9. checkpoint 是严格早于 event tick 的最新完整 checkpoint；
10. 默认 horizon=120。

只允许 selection inputs：tick、region alive、对应 exposure 和 checkpoint availability。事后 cohesion、roots、commits、lineage、entropy 等全部排除。

### 解释

- z-score 是区域内 ranking statistic；
- 不跨 event kind 比较；
- 不跨不同 partition hash 比较；
- 自然峰值不是随机 exposure；
- 两 anchors/seed 先在 seed 内平均。
