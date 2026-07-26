# v0.27 patch notes

- 新增 `event_cohort.py` stable-ID 终点人口构成诊断；
- Simulation 支持 run-local 多 anchor cohort request 与 summary；
- natural-event execution 升级 plan/marker/results/aggregation schema；
- 新增 event cohort delta、恒等式审计与优先人口组件；
- 新增跨结果 synthesis CLI、覆盖分析、诊断优先去重和三份 follow-up plan；
- result audit 支持 v4 并将 demographic claims 标记为 cohort-dependent；
- 修复部分 manifest 仅含某些事件类型时，综合器错误强制生成不存在事件计划的问题；
- 默认世界轨迹与 v0.26 保持一致；
- 发行包继续排除 `docs/archive`，pyproject build-system 不显式依赖 wheel。
