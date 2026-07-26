# Native GUI shared-frame protocol v1

## Authority model

Schema：`subject-evolution-gui-shared-frame-v1`

Python simulation 是唯一权威生产者。共享文件是单向、只读、latest-frame-only 的观察接口。消费者可以跳帧，不能写回世界。

## 文件结构

```text
256-byte global header
slot 0
slot 1
slot 2
```

每个 slot：

```text
64-byte slot header
4 × grid_y × grid_x float32 resources
grid_y × grid_x float32 hazard
max_entities × 72-byte entity records
64-byte aligned padding
```

所有数值均为 little-endian。

## 发布协议

1. 生产者选择非当前 published slot；
2. 将 slot begin/end sequence 清零；
3. 写 resources、hazard 和有效 entity records；
4. 写完整 slot header，begin sequence 与 end sequence 相同；
5. 最后更新 global published slot/sequence/tick。

消费者应：

1. 读取 global published metadata；
2. 读取 slot header；
3. 复制 payload；
4. 再次读取 slot header 和 global metadata；
5. 仅当 sequence、slot、tick 和 slot header 均未变化时接受帧。

`SharedFrameReader` 是该算法的 Python reference implementation。

## Entity record

| 字段 | 类型 | 含义 |
|---|---|---|
| entity_id | uint64 | stable entity ID |
| group_id | uint64 | 当前 group token，0 表示未分组 |
| lineage_id | uint64 | 遗传谱系 ID |
| target_id | uint64 | 当前 intent 的 stable target ID，无目标为 0 |
| x/y | float32 | 世界位置 |
| vx/vy | float32 | 速度 |
| energy | float32 | 当前能量 |
| integrity | float32 | 当前完整性 |
| fertility | float32 | 当前繁殖材料 |
| age_fraction | float32 | age / max_age，截断到 1 |
| generation | uint32 | 世代 |
| action | uint8 | 行动枚举，255 表示无行动 |
| action_success | uint8 | 最近 resolution success |
| flags | uint16 | bit 0：有效实体记录 |

精确 offset、字节数、世界尺寸和 producer 信息由 `<stream>.json` sidecar 发布。

## CLI

```bash
subject-evolution-gui \
  --config configs/d0_orthogonal_environment_smoke.json \
  --output runs/gui_smoke \
  --stream runtime/eco_live.bin \
  --publish-every 2 \
  --backend cpu
```

恢复 trusted checkpoint：

```bash
subject-evolution-gui \
  --resume-checkpoint runs/checkpoints/tick_600.sechk \
  --until-tick 900 \
  --output runs/gui_resume \
  --stream runtime/eco_live.bin \
  --backend cpu
```

历史入口继续可用：

```bash
python -m subject_evolution.gui_interface.run_simulation ...
```

## 生命周期

`RealtimePublisherAttachment`：

- 可作为 context manager；
- attach 时可发布当前初始帧；
- 每 N ticks 发布一次；
- 同一 Simulation 重复挂载会被拒绝；
- detach 恢复原 `step`；
- close 将 sidecar 标记为 `closed` 并释放 mmap。

## 性能边界

CPU reference 路径中，发布主要成本是复制固定环境场和 active entity records。hybrid GPU 路径还需要将环境场转换为 host NumPy，因此高频发布可能增加 D2H 流量。生产长跑应使用较低发布频率，或完全关闭 GUI。
