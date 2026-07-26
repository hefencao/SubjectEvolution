# 架构与提交边界

## 世界循环

```text
配置与版本化 schema
        ↓
环境 / 信息场 / 空间索引 / 社会关系快照
        ↓
只读 observation plan
        ↓
遗传策略 + 动态知识 residual + 工作记忆 + Top-k
        ↓
control proposal → arbitration → action intent
        ↓
只读 conflict resolution plan
        ↓
受控 commit
        ↓
实体 / 环境 / 信息 / 关系 / 生命周期 / 知识 / 主体图更新
        ↓
metrics / logs / checkpoint / offline analysis
```

策略、知识路由、控制器和冲突解析器不得直接写世界。只有消费已版本化计划的提交器可以修改权威状态；提交器可位于 CPU、GPU 或未来的分布式分区，不在架构上永久绑定硬件。

## 权威状态

- CPU reference：所有世界状态由 CPU 语义权威执行。
- GPU strict-reference：验证 GPU/CuPy 可用性，但继续执行 CPU reference 世界，适合当前科学运行。
- GPU hybrid-accelerated：环境/信息场、空间、观察、策略与部分冲突计划可在设备上执行；关系、生命周期、主体图及多项日志仍由 CPU 提交。该路径尚无长程多 tick parity 证明。

## 环境边界

科学核心包含四资源、季节、权威危险场和实体死亡形成的局部死亡痕迹。`additive-environment-field-process-v1` 只允许插件返回有限、非负、同网格形状的标量增量；插件不能读取实体、关系、群组、谱系、策略、知识、记忆或生命周期。

旧 moving Gaussian source 是默认关闭的兼容/娱乐扩展，不属于科学生态基线。具有生命周期和策略的危险主体必须复用现有实体系统。

## 知识层

知识内容、承载副本与承载主体分离。传播需要伙伴机会、注意力、发送/接收能量和容量；本地结果更新副本置信与 outcome 统计。策略只读取经置信、样本、Top-k、工作记忆和计算预算约束后的 residual。

候选知识主体图是诊断结构，不是本体论判定，也不拥有额外世界写权限。

## 群组层

社会群组是高信任关系图上的候选结构。`adaptive-topology-v1` 受最短周期、dirty 状态、信任衰减阈值和最大陈旧期约束。v0.24 的 `freeze-group-refresh` 只冻结后续标签刷新：已有标签保持，死亡成员清除，新生体保持未分组；它是 checkpoint 分支消融，不是新的基线规则。

## 反事实边界

所有科学干预通过注册表声明 kind、target scope 和是否直接控制行动。直接行动替换只允许 entertainment 模式。自然事件矩阵的锚点选择与执行分离，并对源 progress、resolved config、checkpoint 和最终计划记录 SHA-256。

## Manifest 执行边界

v0.25 将锚点规划与分支执行拆成两个不可互换阶段：

```text
run diagnostics → signed exposure-only manifest
                           ↓
                 signed execution plan
                           ↓
        hash preflight → shared trajectories
                           ↓
       per-anchor summaries → seed-level aggregation
```

路径映射只改变文件定位，不改变 manifest。轨迹共享只允许相同 checkpoint SHA-256 和相同 intervention；运行到最大所需 tick 后，各 anchor 仍用自己的 region、event tick 与 horizon 计算结果。完成 marker 必须绑定 manifest hash、checkpoint hash、intervention 和 completed tick。

## Common-boundary evaluation boundary

v0.26 为 paired natural-event trajectory 增加独立评价分区：从共同 checkpoint 冻结稳定实体 ID 与群组 token，后续只对已提交分享流做第二套分类记账。

```text
same checkpoint
   ├─ baseline world ───── current labels ─┐
   │                                      ├─ current-boundary flow
   └─ intervention world ─ current labels ┘

checkpoint stable-ID + group-token snapshot
   ├─ baseline committed shares ──────────┐
   └─ intervention committed shares ──────┴─ common-boundary flow
```

该分区不拥有世界写权限，不改变群组刷新，不进入行动观察。物理槽和稳定实体 ID 必须同时匹配；新生或复用槽位实体属于共同边界之外。它只修正评价口径，不能消除自然事件选择偏差或区域迁移构成。

## Result audit boundary

`natural_event_result_audit` 是纯离线工具。它验证结果、执行计划和 manifest 哈希，读取已计算 delta，分类指标并生成后续执行计划；不得修改原 manifest、重新选择锚点或自动将描述性方向升级为因果事实。

## Event-cohort diagnostic boundary

v0.27 在 natural-event 执行器中增加 run-local stable-ID cohort 观察器。每个 anchor 在自己的 `event_tick` 捕获全局和目标区域的 alive stable IDs，在 `until_tick` 只读取最终已提交实体状态，计算终点人口构成。

```text
event tick stable-ID snapshot
       ↓
shared baseline / intervention world trajectory
       ↓
anchor-specific horizon state
       ↓
retained + survived-outside + absent + existing-in + post-event-born
       ↓
endpoint population balance residual = 0
```

观察器没有世界写接口，不修改 checkpoint payload。共享轨迹可承载多个 anchor 请求，但每个请求的 snapshot tick、region 和 horizon 独立。该分解识别终点身份构成，不记录中间多次迁入迁出，因此不是 pathwise flow ledger。

## Cross-result synthesis boundary

`natural_event_result_synthesis` 是纯离线合并层。它要求全部输入绑定同一 manifest hash，以 anchor/intervention identity 去重，并拒绝核心世界结果不一致的重复分支。诊断完整度只决定在核心结果相同的前提下保留哪份记录。

综合器重新执行 seed-first 聚合、计算 manifest coverage、标注跨事件重复方向并生成新的签名 execution plan；它不得修改原 manifest、补造未执行结果、把自然事件变成随机实验，或从机制近端指标推导人口与主体性结论。
