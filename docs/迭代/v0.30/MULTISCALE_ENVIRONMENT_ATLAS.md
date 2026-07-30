# Multiscale subject–environment atlas

Schema: `multiscale-subject-environment-atlas-v1`

## 环境 signature

每个归一化固定数量区域使用六维 signature：

1. resource 0 / capacity 0；
2. resource 1 / capacity 1；
3. resource 2 / capacity 2；
4. resource 3 / capacity 3；
5. hazard；
6. mortality trace。

v0.30 主线配置同时使用 `2×2`、`4×4`、`8×8`，从大尺度环境块到更细局部生态位进行同一次运行内比较。

## 环境指标

- region signature covariance effective dimensions；
- mean/max pairwise Euclidean distance；
- mean resource spatial CV；
- regional resource-composition effective dimensions；
- temporal turnover：同尺度相邻 evaluation 的 signature 平均绝对变化；
- entity-region effective count。

## 主体暴露指标

每个活实体继承其所在区域的 signature。对 genetic lineage 和 current social group 分别计算：

- between-label exposure variance / total exposure variance；
- eligible label count 和 effective count；
- covered fraction；
- member-weighted mean region-span fraction。

只有至少两个成员的 label 才进入 association，避免 singleton labels 产生机械完美解释。社会群组的 token 0 被排除。

## 尺度解释

不同 scale 的 association 不可直接解释为同一个参数：

- 粗尺度可能把局部差异平均掉；
- 细尺度可能把单一群组分散到多个小区；
- region count 变化会改变 span 的分母；
- fixed normalized partitions 的物理面积随地图大小变化。

因此每个 scale 都携带完整 `SpatialRegionPartition` metadata 和 SHA-256。

## 因果边界

association 表示“实现环境暴露在标签之间有多大差异”，不能区分：

- 环境导致结构形成；
- 结构导致迁移/停留；
- 谱系共同历史导致两者；
- 人口瓶颈或时间趋势同时改变两者。

后续需要 matched checkpoints、环境相位/空间结构干预和结构删除/冻结反事实。
