# 三 seed 有代价传播报告重新评估

用户附上的 v2 报告仍支持以下环境/遗传结论：

- 1500 tick 最终人口为 1334–1386；
- 策略有效维度为 13.96–21.22；
- 资源亲和有效维度为 2.11–2.82；
- 策略维度与动作熵的水平相关在三个 seed 中均很高；
- 死亡压力与凝聚度的水平/偏相关方向重复，但一阶差分较弱。

传播相关部分需要重新解释：

- 报告显示三个 seed 的 `knowledge_transfer_committed_final` 都为 0；
- 同时 `knowledge_cultural_spread_interpretable` 为 true；
- 这是 v0.17 进度字段缺失与分析器判断条件错误造成的矛盾；
- `knowledge_root_genetic_lineage_pair_enrichment_final` 的 7.18、9.68、10.92 使用全部知识根，混入私有经验，不能作为成功文化传播的直接证据。

若原三 seed 运行目录仍存在，可使用 v0.18 的审计工具从 `metrics.csv` 和 `knowledge_transfers.csv` 回填真实传播事件；仅凭现有 v2 汇总文件无法恢复累计成功次数和各窗口拒绝原因。
