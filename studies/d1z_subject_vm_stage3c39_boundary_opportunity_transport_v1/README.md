# Stage 3C-39 action-boundary opportunity transport audit

本 study 只读比较原 panel 与独立 panel 的冻结 Stage 3C-34 crossing assessment，并结合 Stage 3C-36 的 bootstrap transport 结果与 Stage 3C-38 的零阳性复制结果，审计 sampled-action crossing opportunity 为何没有跨 panel 迁移。

允许比较 continuous Subject VM divergence 的频率、幅度、tick 分布和已导出的同 action sampled probability 变化。禁止新增 source、重跑 runtime、调整 exposure 或 crossing definition，也不得从缺失的完整 masked logits 与 categorical draw 推导精确 boundary margin。

冻结结果：独立 panel 的 continuous divergence 并未整体更弱或更早，selected-action probability 变化也不更小；所有已观察幅度指标与原 panel 大量重叠，且不存在一个单调高阈值能分开原 panel 的 crossing source。剩余不确定性被收窄到当前 trace 未记录的 categorical competition 与 draw state。
