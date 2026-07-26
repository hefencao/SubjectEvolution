# v0.31 实现与验证报告

## 源码

新增 `subject_evolution.environment_diversity`，提供共享 CPU/NumPy-device 数学定义和离线审计。CPU `Environment` 与 `DeviceEnvironment` 仅在新 schema 下调用独立波、周期和扩散路径；旧 schema 保留原实现分支。

`EnvironmentAtlasDiagnostics` v2 增加资源自身维度与相关矩阵。Simulation manifest、metrics 和 evolution progress 只在新环境 schema 下发布 `environment_resource_*` 字段。

## 配置

- `configs/d0_orthogonal_environment_smoke.json`
- `configs/mvp_short_d0_orthogonal_environment_longrun.json`

旧配置不会自动启用 D0。

## 回归

- 全量测试：150 passed，1 skipped；
- 跳过：真实 CUDA/CuPy 设备测试；
- 新测试覆盖配置拒绝、外生维度、CPU/模拟设备 parity、atlas v2、manifest、legacy inertness、CLI 和 protocol audit。

## 兼容

v0.30 与 v0.31 使用旧 replay 配置进行 20-tick CPU reference 对照：1974 个共同非计时 metrics 单元无差异，8 类知识日志逐字节一致。v0.30 tick-10 trusted checkpoint 由 v0.31 恢复到 tick 20 后，语义状态与连续 v0.31 一致。

## 解释限制

短程 smoke 最终全局资源有效维度为 3.5183，4×4/8×8 atlas 分别为 3.9149/3.9209；这是集成和动态范围检查，不是演化分化结果。当前没有新的三 seed 长跑，因此不声称生态位、角色或新功能已经涌现。
