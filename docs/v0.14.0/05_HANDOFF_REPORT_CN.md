# Subject Evolution v0.14.0 项目交接报告

## 1. 接手摘要

当前项目已经从单文件模拟器演进为具有 K1-K4 知识体系、完整 checkpoint/replay、可变长度潜知识、量化 L1/L2 路由、计算成本、工作记忆、稀疏知识选择和实体级遗传选择容量的模块化实验系统。

当前版本稳定点：

- `0.14.0`；
- CPU reference 短周期测试通过；
- 旧 schema 兼容性持续验证；
- K2 hybrid 真实 GPU 曾验证至 tick 1000；
- v0.14 新路径真实 CUDA parity 未完成。

## 2. 接手时使用的权威文件

优先读取：

1. `PROJECT_STATUS.md`；
2. `EVOLVABLE_SELECTION_IMPLEMENTATION.md`；
3. `CAUSAL_ABLATION_IMPLEMENTATION.md`；
4. `CPU_GPU_PARITY.md`；
5. `WORKING_MEMORY_IMPLEMENTATION.md`；
6. `SPARSE_KNOWLEDGE_SELECTION_IMPLEMENTATION.md`；
7. `LATENT_ROUTING_COST_IMPLEMENTATION.md`；
8. `LATENT_ROUTER_MLP_IMPLEMENTATION.md`；
9. `LATENT_KNOWLEDGE_IMPLEMENTATION.md`；
10. K1-K4 实现说明；
11. `CHECKPOINT_REPLAY_IMPLEMENTATION.md`；
12. `FINAL_TEST_REPORT.txt`。

## 3. 当前代码状态

### 已实现

- K1 动态内容/副本和有代价交换；
- K2 五维局部后果学习；
- K3 稀疏知识策略 residual；
- K4 知识谱系与候选主体图；
- 完整 `.sechk` 恢复和离线分支；
- 4/8/16/32 维可变潜内容；
- L1 量化线性路由；
- L2 量化两层 MLP 和 L1 shadow；
- 路由/选择/记忆真实能量成本；
- 四维量化工作记忆；
- stable Query-Key Top-k 临时工作集；
- 每实体遗传离散 Top-k 容量；
- 工作记忆和选择器 checkpoint 消融。

### 未实现

- v0.14 真实 CUDA world parity；
- 潜坐标或路由器参数的局部可塑性；
- 持久 device-resident latent arena；
- 单内容/单谱系通用干预；
- 多 seed 长期适应性统计；
- 完整通用主体图数据库和任意嵌套主体；
- 完整主体性评分。

## 4. 当前测试与兼容性

- 64 tests，63 passed，1 CUDA skip；
- 遗传 Top-k 双重复：235 个共同非计时字段、日志和 37 checkpoint 数组一致；
- 固定 K 的 v0.13/v0.14 对照：231 个共同非计时字段和 37 checkpoint 数组一致；
- `.sechk` 恢复在短测试中与连续运行完整状态一致。

## 5. 下一步最高优先级

### P0：真实 GPU parity

在 CUDA 主机上对 `mvp_short_latent_l2_memory_topk_inherited.json` 执行 5-tick reduced world 和 30-tick preserved world parity。若失败，只修首个差异之前的阶段。

验收要求：

- requested capacity 逐位一致；
- selected IDs/scores 逐位一致；
- memory state 逐位一致；
- action、intent、birth/death 逐位一致；
- 持久世界 checkpoint 共同数组一致；
- 成本请求/提交一致。

### P1：多 seed 因果实验

用 5-10 个 seed，多个 intervention tick，比较：

- baseline；
- ablate-working-memory；
- bypass-sparse-selection；
- 固定 K 与遗传 K；
- 预算匹配的计算成本。

报告均值、方差和 paired delta，不只比较一个最终 alive。

### P2：单内容/单谱系消融

从 checkpoint 删除或禁用指定内容的策略贡献，但保留明确的成本和谱系语义。不要直接编辑历史日志。需区分：

- 删除副本；
- 禁止选择；
- residual 置零；
- 保留存储成本；
- 连同维护成本一起消融。

### P3：局部可塑性

若开始实现潜坐标或路由器局部学习，必须：

- 使用独立 schema；
- 不用全局 reward/backprop；
- 明确学习能耗；
- 保留遗传/L1/L2/学习后动作影子；
- 支持 checkpoint 消融；
- 保持定点发布边界。

## 6. 不要重复踩的坑

1. 不要假设不存在的类属性；先读实际源码。
2. 不要用“浮点误差很小”替代离散动作一致性。
3. 不要每 tick 使用不规范的 CuPy FP32 segmented reduction 更新持久场。
4. 不要用 float32 `%=` 假设周期坐标总在半开区间。
5. 不要构造知识 plan 后忘记传给设备 policy。
6. 变体长度变化必须在容量和传输成本审核前预演。
7. 统计不得按 nonzero action 重复累计实体级 selection 工作量。
8. 固定 Top-k 工作集不能写回权威知识 arena。
9. 不要引入全局类别 embedding 作为隐藏共享语义。
10. 不要把单 seed、30 ticks 的 alive 差异解释为适应优势。
11. 不要默认跑 500 ticks；先缩短并定位。
12. GUI wrapper 与核心源码版本必须一致。

## 7. 工作方式偏好

- 用户希望直接推进，不反复请求确认；
- 优先实际修改、测试和交付，不只给建议；
- 单元测试加 20-50 ticks，必要时才延长；
- 每次交付说明真实验证范围；
- 不得声称当前环境完成了真实 CUDA 验证；
- 任何新机制都要有 schema、成本、日志、checkpoint、兼容测试和短对照。

## 8. 建议新会话第一项任务

先在用户真实 CUDA 主机运行 v0.14 world parity。用户上传 `parity_report.json` 后，根据 `first_failure.tick/stage/field/index` 修复；若通过，再建立多 seed 自动实验矩阵，不立即增加新架构。
