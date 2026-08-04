# Stage 3C-40：精确 categorical action-boundary opportunity 审计

本研究复用原 panel 与独立 panel 的 deterministic rank-two source checkpoint，分别运行 `3 tick exposure / 11 tick horizon` 与 `6 / 11` 四臂干预，并开启已通过语义中立性门的 categorical sampling trace。

主要估计量不是后见经验阈值，而是逐事件几何量：原 sampled action 的 CDF interval 到 uniform draw 的最小余量，以及 exposure 延长造成的同一 interval 边界移动。只有边界移动耗尽原余量时才发生实际 sampled-action crossing。

禁止修改 sampling kernel、random stream、exposure、source panel、crossing 定义或 Objective-Fact 语义。
