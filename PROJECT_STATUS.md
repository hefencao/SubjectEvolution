# Subject Evolution 项目状态（v0.20.0）

## 已完成阶段

| 阶段 | 状态 |
|---|---|
| K1–K4 动态知识、副本成本、局部五维后果、策略 residual、内容谱系 | 完成 |
| v0.9 完整 checkpoint、恢复和离线反事实 | 完成 |
| v0.10–v0.12 可变潜知识、L1/L2 路由和物理计算成本 | 完成 |
| v0.13 工作记忆与稀疏稳定 Top-k | 完成 |
| v0.14 遗传 Top-k 容量与 checkpoint 消融 | 完成 |
| v0.15 空间异步四资源生态位与固定预算亲和 | 完成 |
| v0.16 长期选择、世系—群组、知识根和多 seed 工具 | 完成 |
| v0.17 去趋势分析与生态相位反事实 | 完成 |
| v0.18 有代价传播审计和 transfer-only 文化谱系 | 完成 |
| v0.19 局部空间压力与局部凝聚 panel | 完成 |
| v0.20 局部文化传播、区域文化根和局部压力事件反事实 | **完成** |
| 真实 CUDA v0.20 hybrid world parity | 未完成 |
| 三 seed 局部事件正式 checkpoint 因果矩阵 | 未运行 |
| 潜坐标/路由器局部学习 | 未实现 |
| 持久 device-resident latent arena | 未实现 |
| 通用主体图数据库和任意嵌套主体 | 未实现 |

## 用户三 seed、1500-tick 局部压力结果

有代价传播、16 区域的长期结果显示：

- 最终 alive：`1334–1386`；
- 策略有效维度：`13.96–21.22`；
- 资源亲和有效维度：`2.11–2.82`；
- 成功传播：`12,208–14,428`；
- 有效 transferred roots：`2,066.5–2,243.8`；
- 区域人口 CV：`0.125–0.135`；
- 区域死亡压力 CV：`0.653–0.668`；
- 最高局部/全局死亡率：`5.04–7.40×`。

跨 seed 最稳定的局部关系是：

- 同一区域资源稀缺与凝聚度正相关：`0.352–0.422`；
- 稀缺与下一窗口凝聚度正相关：`0.339–0.381`；
- 拥挤与凝聚度负相关：`-0.303～-0.401`；
- 拥挤与下一窗口凝聚度负相关：`-0.205～-0.285`；
- 局部死亡只有弱正相关，危险暴露近于零。

因此不能再使用一个笼统的“生存压力”解释群体凝聚。当前世界更像：资源稀缺促进内部留存，拥挤削弱内部留存；死亡与危险不是主要稳定解释轴。这些仍是观察性关系，需要 checkpoint 干预。

## v0.20 新能力

### 区域传播流

`spatial-local-stress-culture-diagnostics-v2` 在原 4×4 纯分析网格上记录：

- source→destination attempts、commits、bytes；
- 同区域和跨区域传播；
- 各区域 incoming/outgoing rate；
- 每个区域活跃、有效、新建立和消失的 transferred roots；
- 同一文化根是否同时跨区域存活。

这些状态不进入世界控制，不改变知识权威 arena。

### 长期分析 v5

`multi-seed-long-run-analysis-v5` 增加：

- run manifest 后端上下文；
- 局部文化传播 panel；
- 区域固定效应、窗口固定效应、一阶差分和滞后关系；
- 稀缺、拥挤、死亡事件的观察性前后窗口；
- 跨 seed 局部指标符号一致性。

### 局部事件反事实

`local_event_counterfactual.py` 从单个区域的稀缺、死亡或拥挤峰值选择事件，映射到严格早于事件的可信 `.sechk`，配对运行：

- 停止未来知识传播；
- 关闭知识策略 residual；
- 消融工作记忆；
- 旁路稀疏选择器。

所有分支保持同一 checkpoint 和 keyed randomness。

## v0.20 120-tick 验证

seed 10001、200 初始实体、16 区域：

| 指标 | 数值 |
|---|---:|
| Alive | 430 |
| Transfer proposals/attempts/commits | 111 / 111 / 89 |
| Committed bytes | 5,640 |
| Same/cross-region commits | 76 / 13 |
| Active transferred roots | 85 |
| Effective transferred roots | 84.0455 |
| Multi-region active roots | 0 |

验证状态：

- 98 tests：97 passed，1 个真实 CUDA 测试跳过；
- 8 类核心日志 byte-identical；
- 289 个非计时 metrics 字段一致；
- 6 个公开 checkpoint 的 38 个数组一致；
- tick 120 完整 checkpoint 的 331 个数组叶和 26,937 个标量叶一致；
- tick 60 恢复到 tick 120 的权威状态一致；
- v0.19/v0.20 关闭新增功能时，220 个进度共同字段、289 个非计时 metrics 字段和全部共同 checkpoint 状态一致。

## GPU 语义边界

用户以 `--backend gpu` 运行 v0.19 长跑，但配置的 `gpu_semantics_mode` 是 `strict-reference`。在该模式中 GPU 可用性会被验证，权威世界轨迹遵循 CPU reference 语义；这不是 `hybrid-accelerated` 性能验证。v0.20 分析器会从 manifest 明确输出 requested/execution backend、device validation 和 acceleration 状态。

当前构建环境没有真实 CUDA，因此没有独立复现用户 GPU 运行，也没有声明 v0.20 hybrid multi-tick parity。

## 下一步优先级

1. 用 v0.20 local-culture 配置运行 3 seeds × 600–1500 ticks；
2. 从每个 seed 选取区域稀缺和拥挤事件，运行 paired checkpoint 分支；
3. 比较停止传播和关闭知识 residual 对局部凝聚、区域存活、文化根建立/灭绝的影响；
4. 检验文化根是否跨区域持续，并区分同区域留存与跨区域扩散；
5. 在真实 CUDA 主机读取 run manifest，验证 strict-reference 运行身份；
6. 单独推进 hybrid-accelerated parity，不与科学结论混合；
7. 完成局部因果矩阵后，再决定是否增加移动危险源或新的主体控制结构。

暂不采用：人为合成加权总压力、按群组/谱系奖励、提高跨组惩罚、简单提高 mutation rate、全局类别 embedding、普通 Softmax Attention 或更深网络。
