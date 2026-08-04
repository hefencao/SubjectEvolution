# Stage 3C-41：action-logit 与 CDF boundary pressure 来源分解

本研究只读取 Stage 3C-40 已冻结的 categorical trace。它不重跑 runtime，而是在每个 source 已冻结的 top-five boundary opportunity 上分解 masked-logit、softmax probability-mass 与 selected interval endpoint pressure。

运行前，将上一版本的 Stage 3C-40 结果包解压到工作流参数指定的 `stage3c40_root`；不得从摘要重建 trace。

本研究不把 `REST` action port 解释为价值，不拟合 crossing 分类阈值，也不授权 keep/revert、learned weight 或 retention。
