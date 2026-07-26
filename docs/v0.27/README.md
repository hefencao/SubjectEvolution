# v0.27 文档索引

v0.27 不改变默认世界动力学，重点是把自然事件实验从“区域终点值”推进到 stable-ID 人口构成，并把分散的签名结果合并为可审计综合。

## 输入与结论

- 输入：最初 crowding 结果与 `analyses.zip` 中三组后续结果；
- 合并：4 reports、18 anchors、72/108 eligible pairs；
- 重复结果：关闭未来传播在 crowding、mortality、scarcity 中均减少区域 active transferred roots；
- 测量修正：freeze refresh 的 current-label cohesion 下降没有共同边界对应方向，主要由标签分区变化产生；
- 未解决：区域人口缺少 identity composition，且 mortality/scarcity 的三个知识机制尚未执行。

## 本版本文件

- `INPUT_ANALYSES_ASSESSMENT.md`：输入结果、覆盖和结论边界；
- `EVENT_COHORT_DIAGNOSTICS.md`：stable-ID 终点分解与恒等式；
- `RESULT_SYNTHESIS_IMPLEMENTATION.md`：跨结果合并、去重、覆盖与 follow-up 计划；
- `natural_event_result_synthesis.json/.md`：本次实际综合；
- `primary_event_cohort_rerun_execution_plan.*`：18 anchors、64 trajectories；
- `crowding_knowledge_cohort_rerun_execution_plan.*`：6 anchors、16 trajectories；
- `remaining_event_knowledge_cohort_rerun_execution_plan.*`：12 anchors、48 trajectories；
- `V026_V027_COMPATIBILITY_REPORT.json` 与 checkpoint resume report；
- `FINAL_TEST_REPORT.txt`、`PACKAGING_VALIDATION_REPORT.json`；
- `MIGRATION_V027.md` 与 `PATCH_NOTES.md`。

## 建议执行

```bash
python -m subject_evolution.natural_event_execution \
  --execution-plan docs/v0.27/primary_event_cohort_rerun_execution_plan.json \
  --output analyses/primary_event_cohort_rerun \
  --execute --backend gpu --gpu-semantics-mode strict-reference
```

已签名计划不能再附加过滤器或路径改写。需要迁移路径时，从原 manifest 重新构建计划并产生新 hash。
