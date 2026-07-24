# GUI 版本索引与归档可用性

本索引按项目迭代语义整理。`版本包` 指当前工作区中保存的完整 patch archive 或完整源码快照；`直接 diff` 只列出实际存在的文件，不补造缺失文件。

| 版本 | 关键里程碑 | 归档状态 |
|---|---|---|
| v1 | 初始 C++ runtime、共享内存协议、基础 renderer、reader、social loop | 无独立 v1 patch；由 `archives/legacy_baselines/eco_game_runtime.zip` 代表 |
| 前置调整 | 初始渲染调整与当前 GUI 接入补丁 | 两个 legacy archive 均已收录 |
| v2 | 自动 LOD、趋势/Inspector、社会边/rumor 限流 | 完整 patch archive |
| v3 | 事件诊断、局部关系、固定侧栏、环境稳定标尺 | 完整 patch archive |
| v4 | Macro 除零崩溃修复、防御性输入检查、实体形状增强 | 完整 patch archive |
| v5 | raylib shapes texture、UV 和 `TL→BL→BR→TR` 绕序修复 | 完整 patch archive；存在 v4→v5 direct diff |
| v6 | 环境时间滤波、Auto LOD 调整、Macro/Medium 改善 | 完整 patch archive；未发现单独 v5→v6 diff |
| v7 | 恢复 rlgl 高性能路径、自然 Macro、屏幕空间 Medium 采样 | 完整 patch archive；未发现单独 v6→v7 diff |
| v8 | 连续 LOD 权重、环境观察模式、自然跨层过渡 | 完整 patch archive；存在 v7→v8 direct diff |
| v9 | 枯竭资源可读性、hazard 降干扰、Medium 预算与 gradient 改进 | 完整 patch archive；存在 v8→v9 direct diff |
| v10 | 行为形状语义、群体运动/行为聚合、主体色固定为群体身份 | 完整 patch archive；存在 v9→v10 direct diff |
| v11 | 群体历史轨迹、空间椭圆、group focus、环境探针 | 完整 patch archive；存在 v10→v11 renderer/main diffs |
| v12 | 群体直接选择、`[`/`]` 浏览、完整动作构成和群体 Inspector | 完整 patch archive；存在 v11→v12 renderer/main diffs |
| v13 | 3000+ 行 renderer 拆为独立编译单元 | 完整 patch archive；存在 v12→v13 GUI diff |
| v13.1 | 新模块未加入 CMake 导致 undefined reference 的构建修复 | 完整 patch archive；无独立 GUI 功能变化 |
| v14 | PImpl、RenderContext、统一 OverlayBudget、流生命周期、性能计时 | 完整 patch archive；存在 v13.1→v14 diff |
| v15 | 新的干净完整源码快照、F1–F6 观察预设、动作过滤 | 完整源码 snapshot；存在 v14→v15 diff |
| v16 | 稳定群体视觉身份、真实方向箭头、F1 Overview 增强 | 完整源码 snapshot；存在 v15→v16 diff |
| v17 | 群体/区域行为时间滤波和预设稳定化 | 完整源码 snapshot；存在 v16→v17 diff |
| v18 | include 路径修复、observe 性能优化、画面 hold/sample | 完整源码 snapshot；存在 v17→v18 diff |
| v19 | OpenGL 3.3/4.3 实体 GPU instancing，CPU 回退 | 当前完整源码 snapshot；存在 v18→v19 diff |

## 路径

- v2–v14：`archives/version_packages/`
- v15–v19：`archives/full_source_snapshots/`
- direct diffs：`patches/direct_diffs/`
- apply scripts：`scripts/`
- 每版说明：`docs/version_notes/`
- 当前展开源码：`current/gui_v19_expanded/`

## 注意

部分版本 archive 内部会重复携带前序说明或源码用于基线确认，因此不要把所有 archive 依次覆盖到同一个工作树。需要当前功能时直接使用 v19 完整源码。需要历史追踪时查看对应 archive 和 direct diff。
