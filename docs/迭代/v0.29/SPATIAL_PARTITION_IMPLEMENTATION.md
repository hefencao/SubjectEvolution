# Spatial partition implementation

## 目标

此前 local stress 与 event cohort 各自实现区域映射，且 manifest 没有完整物理几何 provenance。v0.29 引入 `SpatialRegionPartition`，让所有诊断与规划共享同一实现。

## Schema

`normalized-fixed-count-grid-v1`

输入：world width/height、world grid x/y、regions x/y。输出：

- stable row-major region IDs；
- normalized/physical bounds；
- physical region width/height；
- world cells per region；
- grid alignment；
- normalized topology SHA-256；
- complete physical partition SHA-256。

## 使用位置

- `local_stress.py`：区域压力与文化 panel；
- `event_cohort.py`：event-region stable-ID cohort；
- `natural_event_matrix.py`：anchor bounds、partition audit 和 mixed-geometry guard；
- `simulation.py`：run manifest/metadata/scientific validity；
- `long_run_analysis.py`：跨 seed context；
- `protocol_audit.py`：可读协议报告。

## 兼容

旧 checkpoint 恢复时按 embedded config 重建 partition。旧 manifest v1 可继续读取；若 resolved config 无物理几何，只发布 legacy/inferred topology，不伪造 partition hash。

## 非目标

该实现不改变环境网格、实体移动、伙伴采样或世界提交，也不声明固定-count regions 在不同地图上尺度不变。
