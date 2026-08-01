# 设计边界

## 纪元

- 纪元不是人为奖励阶段，而是证据资格边界。
- 每个新纪元必须从通过预注册进入合同的完整 checkpoint 开始。
- base checkpoint 连同 qualification、registry 和 SHA-256 锁冻结。
- 后续小实验可从 base checkpoint 分支，避免重复演化整个前史。

## 区域分支 v1

保留：

- 原始完整环境网格、周期相位、资源场、地形、信号介质和全局坐标；
- 区域内实体的 genotype、谱系、身体、知识和内部关系；
- checkpoint tick、随机键和累计世界计数。

裁剪：

- 区域外活跃实体；
- 指向区域外实体的关系；
- 跨边界延迟直接消息；
- 尚未提交的场信号 emission queue。

区域裁剪属于显式 intervention，不是 exact replay。真正缩小物理网格前，必须实现原世界坐标偏移、边界物质/信息通量及 halo 合同。
