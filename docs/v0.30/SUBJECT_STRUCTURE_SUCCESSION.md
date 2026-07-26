# Candidate-subject succession

Schema: `stable-membership-subject-succession-v1`

## 目的

此前 `CandidateSubjectGraph` 能表示当前身体、遗传谱系和社会群组节点，但其 summary 主要是当前截面。v0.30 增加独立 succession tracker，回答：候选群组在相邻实际 refresh 之间如何延续、分裂、合并或消失。

## 输入边界

每次 `SocialSystem` 真正提交一个新的 `GroupLabelPlan` 后，tracker 读取：

- group token；
- canonical member segments；
- 物理槽位上的 stable entity ID。

它不读取行动偏好、控制器、知识内容、收益结果或未来状态，也不修改 group plan。

## 转换定义

前一 refresh 的群组 `A` 与当前群组 `B` 只要共享至少一个 stable entity ID，就存在 overlap edge。

- current 无 predecessor：formation；
- previous 无 successor：dissolution；
- previous 连接多个 current：split source；
- current 连接多个 previous：merge target；
- token 相同：same-token continuity；
- token 相同且成员集合完全一致：exact-membership continuity；
- 历史见过、上一 refresh 不活跃、当前重新出现：reactivation。

每个 current group 选择最大成员交集 predecessor，报告：

- Jaccard；
- source retention；
- target inheritance。

聚合时按 current member count 加权，避免小群组与大群组获得相同权重。

## Stable ID 与槽位复用

成员身份完全由 stable entity ID 决定。相同物理槽位若已被新生实体复用，不产生继承边。

## 不进入主体图的原因

Succession edge 是观察性结构关系，不是世界内控制或成员关系。直接写入 `CandidateSubjectGraph` 会把诊断推断升级为模拟事实，因此 v0.30 保持独立日志和 checkpoint accounting state。

## 尚未实现

- 任意嵌套主体；
- 社会群组之上的群组；
- 结构删除反事实；
- 主体身份评分；
- persistence、repair、control、benefit flow 的联合判据。
