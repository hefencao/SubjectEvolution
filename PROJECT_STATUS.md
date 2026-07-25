# Subject Evolution 项目状态（v0.21.0）

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
| v0.20 局部文化传播、区域文化根和局部压力事件反事实 | 完成 |
| v0.21 局部死亡痕迹感知、自适应群组刷新、旧 checkpoint 哈希兼容 | **完成** |
| 真实 CUDA v0.20 hybrid world parity | 未完成 |
| 三 seed 局部事件正式 checkpoint 因果矩阵 | 未运行 |
| 潜坐标/路由器局部学习 | 未实现 |
| 持久 device-resident latent arena | 未实现 |
| 通用主体图数据库和任意嵌套主体 | 未实现 |

## v0.21 方向调整

三 seed 局部文化分析显示：稀缺与新文化根出现正相关，但与净文化根建立负相关；拥挤稳定提高知识外流；死亡与 incoming transfer 只有弱关系。这支持暂停继续扩展相关分析，转向主体可感知结构和环境多元化。

v0.21 新增：

- `local-decaying-mortality-trace-v1`：死亡位置沉积无身份局部痕迹，衰减和扩散后只进入公开 danger observation，不增加物理伤害或直接奖励；
- `adaptive-topology-v1`：根据关系拓扑变更、trust 阈值衰减和最大陈旧期限刷新群组标签；
- 新旗舰长跑配置使用最小刷新间隔 100、最大陈旧 300；
- 旧配置继续使用 `periodic-v1`，没有改变兼容默认；
- 修复新版 dataclass 默认字段导致 v0.20 `.sechk` 配置哈希误判的问题。

120-tick 对照中，自适应刷新将群组重算从 3 次降至 2 次；死亡痕迹在首次死亡后进入策略轨迹。两者都会改变世界结果，当前只验证机制和确定性，不宣称长期适应优势。

最终验证：105 passed，1 个真实 CUDA 测试跳过。

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

1. 用 v0.21 mortality-trace + adaptive-group 配置运行 3 seeds × 600–1500 ticks；
2. 检查死亡痕迹是否形成可遗传的空间响应，而不是只看死亡率相关；
3. 比较 adaptive 与 periodic 群组刷新下的长期标签稳定、策略维度和文化传播；
4. 扩展真实环境轴：移动危险源、伤害类型、遮蔽/通行成本或资源转换链；
5. 主体结构优先推进遗传性危险证据混合、可配置任意信息通道 schema 和局部后果预测；
6. 单独完成真实 CUDA hybrid parity，不与科学结论混合。

暂不采用：直接暴露全局死亡计数、按群组/谱系奖励、全局类别 embedding、普通 Softmax Attention、提高跨组惩罚或单纯提高 mutation rate。
