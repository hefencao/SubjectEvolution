# Crowding paired-intervention result assessment

## 覆盖

输入结果完整覆盖所选 execution plan：3 seeds、6 个 crowding anchors、3 个干预，共执行 16 条共享轨迹，去重 8 条 branch。preflight 的 checkpoint、progress 与 resolved config 均存在且哈希匹配。

## 可支持结论

### 传播维持局部文化状态

关闭未来知识传播后，区域 incoming/outgoing commits 在所有分支均为 0，操作检验通过。三个 seed 的区域 active transferred roots 均下降，seed-level 平均变化为 `-84.33`。这支持“传播在 crowding 事件后的 120-tick horizon 内维持局部 transferred-root 状态”。

该结论是机制近端结论，不证明传播提高人口、凝聚度、遗传多样性或适应度。区域 alive 的方向为 2 正 1 负，人口收益未建立。

### 群组刷新结果暂受测量耦合

冻结群组刷新后，原 current-label cohesion 在三个 seed 均下降，seed-level 平均为 `-0.2103`。但 cohesion 使用的标签正是干预对象，因此不能据此称“刷新提高社会凝聚”。v0.26 已生成 8-trajectory 共同边界复跑计划。

### 资源亲和值得跨事件复制

中和资源亲和后，crowded-region alive 在三个 seed 均增加，seed-level 平均为 `+7.33`。但区域 alive 混合了存活、出生、死亡和迁移，且目前只覆盖 crowding。应先复制到 scarcity/mortality，并增加固定 cohort/retention 诊断，再讨论亲和表型的适应成本。

## 后续优先级

1. 先运行 8 条共同边界复跑；
2. 再运行 48 条 scarcity/mortality × 当前三个干预；
3. 最后运行 16 条 crowding × knowledge-policy / working-memory / Top-k 消融。

原始事件暴露仍是自然发生而非随机分配，所有解释限定于预注册 checkpoint 与 horizon。
