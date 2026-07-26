# v0.29 patch notes

## 配置新增

`run`：

```json
{
  "spatial_stress_region_schema": "normalized-fixed-count-grid-v1"
}
```

`social`：

```json
{
  "group_label_schema": "trusted-directed-fixed-round-min-label-v1",
  "group_label_propagation_rounds": 8
}
```

旧配置缺省得到相同语义。项目内配置已显式写入字段。

## Manifest

新生成 manifest 为 v2，发布 region geometry 和 candidate ranking。旧 v1 manifest 仍可用于已有签名计划与结果审计。

默认跨 run 要求 region topology/physical geometry 一致。需要跨尺度探索时使用 `--allow-mixed-region-partitions`，并在分析中按 partition hash 分层。

## Long-run analysis

输出 schema 从 v7 升为 v8，仅增加 protocol provenance，不修改历史指标计算。

## Build

`pyproject.toml`：

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"
```
