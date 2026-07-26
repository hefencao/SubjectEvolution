# Natural-event result audit

`subject_evolution.natural_event_result_audit` 支持读取 v0.25 results v2 和 v0.26 results v3，并验证 result、execution plan 与可选 manifest 的哈希链。

审计将指标分为：

- manipulation check：transfer incoming/outgoing commits；
- mechanism-proximal：new/lost/active transferred roots；
- current-label boundary：原 cohesion；
- checkpoint-common boundary：v0.26 reference cohesion；
- downstream region state：alive、mortality、scarcity。

同一 seed 的多个 anchor 先平均，再统计跨 seed 方向。只有三个 seed 同号时才列为 repeated direction，且仍明确标记为描述性结果。

若提供完整 manifest，审计器可生成：

1. `common_boundary_rerun`：对已运行的 freeze-group-refresh 锚点复跑共同边界；
2. `remaining_event_replication`：把当前机制复制到尚未运行的 event kinds；
3. `remaining_mechanism_ablation`：在当前 event kind 补齐尚未执行的 eligible interventions。

审计器不执行分支，不改变 manifest，也不根据结果重新选择锚点。

生成的 JSON 是可直接执行的签名 execution plan：

```bash
python -m subject_evolution.natural_event_execution \
  --execution-plan <followup_execution_plan.json> \
  --output <new-output> --execute --backend gpu \
  --gpu-semantics-mode strict-reference
```

签名计划模式拒绝额外 filter 或路径映射，避免执行时静默改变预注册范围。
