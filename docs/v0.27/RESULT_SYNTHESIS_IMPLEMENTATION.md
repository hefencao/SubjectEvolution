# Natural-event result synthesis implementation

入口：

```bash
python -m subject_evolution.natural_event_result_synthesis \
  --results <result-json-or-directory> [--results ...] \
  --manifest <natural_event_matrix_manifest.json> \
  --output <output-directory>
```

## 合并规则

1. 输入支持 paired results v2、v3、v4；
2. 所有报告必须绑定同一 manifest SHA-256；
3. 主键为 `(anchor_id, intervention)`；
4. 重复分支的核心世界结果不一致时拒绝合并；
5. 核心结果一致时，按 event cohort > common boundary > plain 的诊断完整度保留；
6. anchor 不作为独立重复，聚合始终先 seed 内平均；
7. 跨事件方向只在每个事件自身满足 seed 方向判据后登记。

## 本次综合

- reports：4；
- anchors：18；
- observed pairs：72；
- expected pairs：108；
- transfer cultural-state direction：3 event classes；
- cohort coverage：0。

## 自动后续计划

综合器只在 manifest 中确有匹配锚点和 eligible intervention 时生成计划，避免部分 manifest 被强制套用不存在的事件类别。

- primary cohort rerun：三主要机制 × 全部事件；
- crowding knowledge cohort rerun：已执行 crowding knowledge mechanisms 加 cohort；
- remaining event knowledge cohort rerun：补齐 mortality/scarcity 知识机制。

计划是新签名 artifact，不修改原 manifest。综合器不执行轨迹、不填补缺失结果、不把跨事件同向升级为普遍因果规律。
