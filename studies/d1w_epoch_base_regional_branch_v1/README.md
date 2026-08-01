# D1-W 纪元基线与区域分支基础

本 study 建立两项基础设施：

1. 用显式进入合同把合格的大规模长程 checkpoint 冻结为下一纪元的 base checkpoint；
2. 从纪元基线建立区域 active-set 分支，裁剪区域外实体、跨边界关系和延迟消息，同时保留完整环境坐标系与场状态。

区域分支 v1 不是物理网格缩小。它优先避免局部网格重建造成季节相位、资源回流和边界通量漂移。它适合从大规模世界提取较小实体集合进行机制开发，但不能被解释为原世界的无偏缩小版。

当前关系形成仍由 SHARE 成功/失败的固定 trust 增减驱动，不满足 `epoch-1-entity-subject-prototype` 进入门。当前 group 仍是关系阈值连通分量，不满足 `epoch-2-group-subject-prototype` 进入门。
