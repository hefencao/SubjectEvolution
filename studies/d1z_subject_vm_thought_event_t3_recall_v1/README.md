# ThoughtEvent T3：最小前向 recall 机制 smoke

本主体能力演化分支只验证一条最小、确定性且无固定认知角色的前向 recall 路径：每个主体从统一 ThoughtEvent arena 中读取最近一个严格早于当前 tick 的已提交事件，并通过 fixed-bootstrap node 9 的声明式 ingress 进入统一 Subject Graph。

冻结四臂：

- `no-recall`：完全关闭 recall；
- `identity-recall`：读取 parent token 原内容；
- `rotate-one-coordinate-control`：保持 parent identity、age 与成本不变，循环置换 token coordinate；
- `zero-content-equal-cost-control`：保持 selector、parent DAG 与全部计数成本，读入零内容。

Recall ingress 只连接 readout-only node 9，不拥有 action output。T3 只证明 selector、graph ingress、parent DAG、checkpoint 与成本链路可运行；不证明延迟信息效用、思维链、分布式认知、语言、长期记忆或 retention 资格。
