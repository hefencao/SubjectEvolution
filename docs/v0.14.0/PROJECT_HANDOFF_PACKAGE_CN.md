% Subject Evolution v0.14.0 项目说明、进度与交接报告
% 交接版本：2026-07-24

> 本文依据 v0.14.0 实际源码、项目状态、测试报告和阶段实现文档整理。真实 CUDA v0.14 world parity 尚未完成。

# 目录

- 项目总览
- 项目进度
- 架构与科学边界
- 当前交接报告
- 运行手册
- 版本与 Schema 矩阵
- 新聊天启动提示词
- 交付物索引

\newpage

# 项目总览


## 1. 项目目标

`Subject Evolution` 是一个用于研究嵌套主体、局部知识、社会关系和演化机制的可复现实验模拟器。项目关注的不是训练一个外部最优智能体，而是让实体、知识副本、社会群组和候选知识主体在显式物理成本、局部信息与稳定因果边界中演化。

核心问题包括：

- 个体如何依据局部环境、身体状态、关系与信息行动；
- 知识如何创建、复制、损坏、验证、遗忘和跨宿主延续；
- 知识如何在不绕过公开决策边界的情况下影响行动；
- 表达容量、计算、存储、传播和验证成本如何形成选择压力；
- 知识内容是否表现出持续性、复制、宿主分布、利益边界和策略影响等候选主体特征；
- 如何通过 checkpoint、共同随机数和离线分支进行可重复反事实实验。

## 2. 科学原则

### 2.1 局部因果

实体和知识只读取当前或已提交的局部状态，不读取未来信息、全局适应度或集中 reward。五维后果保持为：

1. 能量变化；
2. 完整性变化；
3. 物质/资源变化；
4. 信息变化；
5. 繁殖机会变化。

它们不会被系统提前压缩为单一全局奖励。

### 2.2 公开控制边界

知识和记忆可以影响策略，但必须通过公开接口：

```text
observation
  -> policy logits / sparse residual proposal
  -> energy budget arbitration
  -> sampled action
  -> intent
  -> resolution
  -> commit
```

知识内容、候选主体图和诊断器不能直接替换动作或绕过物理结算。

### 2.3 物理与计算成本

模拟计入：

- 身体维持和移动；
- 信号与知识传输；
- 知识存储、验证和维护；
- 潜路由计算；
- 稀疏候选选择；
- 工作记忆更新。

无法支付的计算 residual 采用稳定的 `all-or-none-per-entity-v1` 规则整体拒绝。

### 2.4 确定性与兼容性

- 使用稳定实体 ID、counter-based 随机流和规范化排序键；
- 离散决策和 ID 字段要求逐位一致；
- 浮点持久场采用 reference-order 归约或规范化发布；
- 新机制使用独立 schema，关闭时必须保持旧版本共同状态和日志兼容；
- 完整 `.sechk` 支持同 checkpoint 分支与共同历史反事实。

## 3. 总体架构

```text
配置与 Schema
      |
      v
环境/信息场 ---- 空间索引 ---- 社会关系/群组
      |                |             |
      +---------- Observation Plan --+
                       |
          遗传基础策略 + 知识/记忆机制
                       |
         稀疏 residual + 计算成本审核
                       |
                 Policy Decision
                       |
                    Intent
                       |
              Conflict Resolution
                       |
                    Commit
                       |
      实体/环境/信息/关系/知识/记忆更新
                       |
        Metrics / Logs / Checkpoint / K4 诊断
```

## 4. 主要模块

| 模块 | 文件 | 作用 |
|---|---|---|
| 配置与 schema | `config.py` | 校验版本化策略、知识、成本、记忆和选择配置 |
| 世界主循环 | `simulation.py` | tick 阶段、计划/提交、指标、checkpoint |
| 环境与信息 | `environment.py`, `information.py` | 资源、危险、信号、延迟消息 |
| 空间与社会 | `spatial.py`, `social.py` | 周期空间、邻居、信任、群组 |
| 策略 | `policy.py` | 遗传 logits、知识 residual、动作采样 |
| K1/K2 知识 | `knowledge.py` | 内容目录、副本 arena、传播、验证、五维后果 |
| K3 知识策略 | `knowledge_policy.py` | 稀疏 residual 与贡献审计 |
| K4 候选主体 | `knowledge_subjects.py` | 内容谱系、边界流、候选图诊断 |
| 潜知识 L1/L2 | `latent_knowledge.py` | 可变长度 int16 latent、线性/MLP 路由、Top-k |
| 工作记忆 | `working_memory.py` | 四维定点短期状态和 prediction error 更新 |
| 计算成本 | `routing_cost.py` | 路由/选择预算和归因 |
| checkpoint | `checkpointing.py` | 可信 `.sechk` 完整世界序列化 |
| 重放/干预 | `replay.py`, `interventions.py` | 延续、共同历史分支、科学消融 |
| GPU runtime | `gpu_runtime.py`, `gpu_environment.py` | hybrid 设备路径和 host/device 同步 |
| parity | `parity.py` | 首个 CPU/GPU 语义差异定位 |

## 5. 当前最高能力路径

配置 `configs/mvp_short_latent_l2_memory_topk_inherited.json` 同时启用：

- 可变长度潜知识 `4/8/16/32`；
- L2 量化两层 MLP 路由；
- 路由计算成本；
- 四维量化工作记忆；
- 稳定 Query-Key Top-k 临时工作集；
- 实体级遗传容量等级 `0/1/2/4/8`；
- 完整 checkpoint；
- 科学模式与 strict-reference GPU 语义。

## 6. 权威状态与临时计算视图

权威知识状态是动态 SoA 内容/副本 arena。Top-k 只是每 tick 可重建的临时工作集：

- 不限制真实知识数量；
- 不删除未选择的知识；
- 不改变传播、损坏、验证和谱系；
- 不使用全局类别 Embedding；
- 不采用普通 float Softmax Attention。

## 7. 项目目录

```text
configs/                         实验配置
src/subject_evolution/           核心源码
tests/                           单元与语义测试
scripts/                         parity 和短矩阵脚本
docs/                            原始设计与 checkpoint 文档
*_IMPLEMENTATION.md              各阶段实现说明
*_CONTROL_MATRIX_REPORT.md       短周期条件对照
*_VALIDATION_REPORT.json         机器可读验证
PROJECT_STATUS.md                当前权威状态
SPLIT_MANIFEST.md                文件拆分与版本新增索引
```

## 8. 非目标和未实现范围

当前没有声称实现：

- 完整任意嵌套主体数据库；
- 单一、最终的主体性真值评分；
- 外部集中训练、backprop 或 Hero RL；
- 全局类别 Embedding 控制表；
- 任意连续潜长度和 JIT kernel；
- 持久 device-resident latent arena；
- v0.14 真实 CUDA 多 tick world parity；
- 多 seed 长期适应优势证明。
\newpage

# 项目进度


## 1. 初始工程化

原始单文件约 8938 行，拆分为 backend、config、environment、information、policy、social、simulation 等模块；删除了误嵌入 Python 文件的 PowerShell 命令，并建立包结构、配置和测试入口。

## 2. 关键版本时间线

| 版本/阶段 | 主要完成内容 | 当前状态 |
|---|---|---|
| K1 / v0.5 | 动态知识内容与独立副本、容量、存储/传输成本、交换、损坏、遗忘、淘汰 | 完成 |
| K2 / v0.6 | 本地 context/action 的五维后果统计、私有经验、接收知识后续本地验证 | 完成 |
| v0.6.1-v0.6.5 | CPU/GPU parity 工具、FP32 分段归约修复、周期坐标上界修复 | K2 hybrid 真实 GPU 验证至 tick 1000 |
| K3 / v0.7 | 知识副本通过稀疏 residual 影响公开策略 logits；遗传与知识动作对照 | 完成 |
| K4 / v0.8 | 知识内容/变体谱系、宿主分布、边界流、成本与策略影响候选主体图 | 完成，diagnostic-only |
| v0.9 | 完整 `.sechk` 世界恢复、离线延续和共同历史反事实分支 | 完成 |
| v0.10 | 可变长度 `int16` 潜知识 L1 量化线性路由，长度变异和真实字节成本 | 完成 |
| v0.11 | L2 遗传量化两层 MLP、integer hard-tanh、L1 shadow 对照 | 完成 |
| v0.12 | 路由计算能耗、预算仲裁、K4 路由成本归因、预算匹配实验 | 完成 |
| v0.13 | 四维量化工作记忆、稀疏 Query-Key stable Top-k、选择成本 | 完成 |
| v0.14 | 实体级离散遗传 Top-k 容量、工作记忆与选择器 checkpoint 消融 | 完成 |

## 3. K1-K4 进度

### K1：知识作为世界内部副本

实现内容、独立副本、宿主容量、编码字节、传输尝试/丢失/损坏/提交、存储维护、发送/接收成本和稳定淘汰。K1 不影响策略。

### K2：知识的局部经验

每个副本保存 context/action 匹配下的五维 outcome mean、样本数、置信度和验证 tick。接收知识不会立即被视为本地事实，必须在后续匹配经验中验证。

### K3：知识影响公开策略

知识按 holder、context 和 action 形成稀疏 action-logit residual。系统分别记录遗传 logits、知识 logits、遗传动作和最终动作。未验证外来知识只能按显式折扣参与。

### K4：知识内容候选主体图

追踪内容、父子变体、根内容、唯一宿主、跨宿主持续、群组/谱系/区域分布、传播边界、成本和策略影响。K4 不参与控制，不输出单一主体性真值。

## 4. CPU/GPU 一致性历史

### 已定位并修复

1. `sensor_quality` dtype 不一致；
2. NumPy/CuPy `reduceat` 的 FP32 段内求和顺序导致 `information.source` 和资源场累积偏差；
3. `float32` 周期取模可能得到精确世界上界，导致位置不变量失败；
4. hybrid GPU 路径构造知识 plan 后未传给 `policy.decide()`；
5. parity 工具曾错误假设不存在的 `relation_target` 属性，现已改为按真实结构比较。

### 已验证范围

用户在真实 GPU 上确认：

- `mvp_short_k2_exchange` hybrid 路径运行至 tick 1000 未发现偏差；
- 周期位置修复后原异常不再出现。

### 尚未验证范围

v0.10-v0.14 的以下组合尚未完成真实 CUDA 多 tick world parity：

- 可变长度 latent；
- L1/L2 路由；
- 路由能量预算；
- 工作记忆更新；
- stable Top-k 选择；
- 实体级遗传容量；
- 相关 checkpoint 干预状态。

正式科学 GPU 运行默认使用 `strict-reference`；`hybrid-accelerated` 是实验路径。

## 5. 当前验证结果

v0.14.0：

- 64 tests；
- 63 passed；
- 1 skipped：当前环境无 CuPy/CUDA；
- 遗传容量条件双重复的 235 个共同非计时指标、核心日志和 37 个 checkpoint 数组一致；
- 固定 K 模式与 v0.13 的 231 个共同非计时字段、日志和 37 个 checkpoint 数组一致。

短实验使用单 seed、30 ticks，证明机制生效、确定且兼容，不证明长期适应优势。

## 6. v0.14 短实验摘要

固定 K=4 与实体级遗传容量比较：

| 条件 | Alive | Births | L2 MAC | 路由能耗 | 说明 |
|---|---:|---:|---:|---:|---|
| 固定 K=4 | 595 | 95 | 16,878,272 | 0.738006 | v0.13 兼容基线 |
| 遗传容量 | 589 | 89 | 9,884,280 | 0.528154 | 容量等级 0/1/2/4/8 |

单 seed、30 ticks 中，遗传容量减少约 41.44% L2 MAC 和 28.44% 路由能耗；不能据此判断适应性优劣。

checkpoint tick 15 的消融到 tick 30：

- 清零并冻结工作记忆：最终 alive 相对基线 `+18`；
- 绕过 Top-k 但保留全部知识：最终 alive `+3`，路由能耗增加约 `0.215273`。

这些结果证明机制具有因果影响，但同时改变成本，不可直接解释为功能有益或有害。

## 7. 下一阶段候选

优先级建议：

1. 真实 GPU v0.14 parity；
2. 多 seed、多 intervention tick 的记忆/选择消融；
3. 单内容和单谱系 checkpoint 消融；
4. 更长但受控的容量性状选择实验；
5. 潜坐标或路由器的局部学习；
6. 持久 device-resident latent arena。
\newpage

# 架构与科学边界


## 1. 不可破坏的边界

### 1.1 新机制必须独立 schema

任何新策略、知识、记忆、选择或成本规则必须使用独立版本化 schema。关闭模块时，旧配置的共同状态、日志和 checkpoint 应保持一致。

### 1.2 知识不能绕过公开接口

“知识不是隐藏控制器”并不禁止潜空间或小型网络。它要求：

- 参数来源可追踪；
- 不由外部全局优化器注入；
- 不直接替换动作；
- 对 logits、动作和成本的贡献可审计；
- 可以通过 checkpoint 消融验证因果作用。

### 1.3 五维后果不等于五种知识类别

能量、完整性、物质、信息和繁殖机会是统一物理后果坐标，不是固定知识类别。潜内容可以动态、变长和多元，但后果审计仍保持五维。

### 1.4 权威状态与临时视图必须分离

- 权威知识：动态内容/副本 SoA；
- 临时视图：每 tick Top-k 工作集、GPU 长度桶；
- 临时视图不能写回成为真实知识容量；
- 未选知识仍可维护、传播、验证和形成谱系。

### 1.5 成本必须进入真实世界

存储、传播、验证、路由、选择和记忆更新不能只记 metrics。已启用的成本必须扣除真实能量；预算不足的行为要有确定性仲裁和审计。

## 2. 已明确不采用或暂缓的方案

### 固定 `K_max` 作为权威知识容量

不采用。它会截断知识多样性并将临时 GPU 工作集误当作世界状态。固定矩阵只可作为 ephemeral device workset。

### 全局类别 Embedding 控制表

不采用为权威控制输入。若由设计者或外部训练定义，会引入共享预设语义。未来可用于离线聚类或 GUI 分析。

### 普通 float Softmax Attention

暂缓作为正式科学路径。风险包括 `exp`、归约顺序、相对稀释、CPU/GPU parity 和逐知识因果归因。未来只能作为独立 schema，并需要定点/规范化发布和成本模型。

### 全局 reward、backprop、外部集中训练

不适合当前项目目标。局部遗传、局部经验和世界内成本可以保留；外部优化器会改变实验问题。

### 未经验证的单一主体性评分

不输出。K4 只保留 persistence、replication、distribution、cost、policy influence、boundary cohesion 等分量，并明确 diagnostic-only。

## 3. 修改后可能保留的方向

必须避免退化和预设：

- 固定槽：只作为临时 Top-k GPU 缓冲；
- embedding：只作为内容自身状态、宿主局部原型或离线分析结果；
- Query-Key：使用内容 latent、宿主公开状态与记忆，不使用预设类别；
- Attention：优先 stable Top-k 和整数 score，普通 Softmax 需另立实验 schema；
- 工作记忆：定点、可遗传、有成本、后果提交后更新；
- 更复杂路由：必须保留 L1/L2 影子基线和逐层审计。

## 4. 数值一致性原则

- 公开决策边界优先整数/定点；
- 不让微小 float 误差直接跨过离散动作边界；
- GPU 大批量计算可以使用设备，但最终归约/发布必须有规范顺序；
- stable Top-k 使用 `(-score_q, copy_id, content_id)`；
- 持久场的重复格点归约采用 CPU reference 顺序或明确规范；
- 周期位置必须规范到半开区间 `[0, extent)`，不能只依赖 float32 `%=`。

## 5. 反事实解释原则

观察到模块改变 alive 或 mean energy 时，不能直接说模块有益或有害。干预可能同时改变：

- 信息状态；
- 计算成本；
- 被选择的知识；
- 行动概率；
- 后续知识创建与传播。

可信解释应使用：

1. 同 checkpoint；
2. 同稳定随机流；
3. 单一明确干预；
4. 分别报告动作、成本、世界状态和知识状态；
5. 多 seed 与多个 intervention tick；
6. 不把短周期差异解释为长期适应优势。

## 6. GUI 与核心包边界

当前 v0.14.0 交付包不包含 `src/subject_evolution/gui_interface/`。用户本地 GUI wrapper 曾调用同一个 `Simulation.step()`，因此核心异常应在 simulation 层定位。继续开发时要确认 GUI 使用的源码版本与核心包一致，避免 GUI 目录中残留旧模块副本。
\newpage

# 当前交接报告


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
\newpage

# 运行手册


## 1. 解压与环境

```bash
unzip subject_evolution_v014_project.zip
cd subject_evolution_v014_project
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\\Scripts\\activate
python -m pip install -U pip
python -m pip install -e .
```

项目声明的必需依赖只有 `numpy>=1.24`。GPU 运行还需要与本机 CUDA runtime 匹配的 CuPy，并确保 Python 能检测到可用设备。

若不执行 editable install，也可：

```bash
export PYTHONPATH="$PWD/src"
```

PowerShell：

```powershell
$env:PYTHONPATH = "$PWD\src"
```

## 2. 快速 CPU 冒烟

```bash
PYTHONPATH=src python -m subject_evolution.cli \
  --config configs/smoke_cpu.json \
  --output runs/smoke_cpu \
  --backend cpu
```

最新机制的 30-tick 短运行：

```bash
PYTHONPATH=src python -m subject_evolution.cli \
  --config configs/mvp_short_latent_l2_memory_topk_inherited.json \
  --output runs/v014_inherited \
  --backend cpu
```

## 3. GPU 模式

### 3.1 正式正确性优先

```bash
PYTHONPATH=src python -m subject_evolution.cli \
  --config configs/mvp_short_latent_l2_memory_topk_inherited.json \
  --output runs/v014_gpu_strict \
  --backend gpu \
  --gpu-semantics-mode strict-reference
```

该模式要求存在可用 GPU，但以 CPU reference 世界语义为权威，不代表获得 hybrid 加速。

### 3.2 实验 hybrid 路径

```bash
PYTHONPATH=src python -m subject_evolution.cli \
  --config configs/mvp_short_latent_l2_memory_topk_inherited.json \
  --output runs/v014_gpu_hybrid \
  --backend gpu \
  --gpu-semantics-mode hybrid-accelerated
```

v0.14 的真实 CUDA world parity 尚未完成；此输出不应自动作为正式科学基线。

## 4. 测试

```bash
PYTHONPATH=src python -m compileall -q src tests
PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py' -v
```

当前权威结果：64 tests，63 passed，1 skipped（无 CuPy/CUDA）。

开发偏好：先跑相关单测和 20-50 ticks 短验证；只有问题在长轨迹出现时才扩展到更长运行。

## 5. CPU/GPU parity

短阶段检查：

```bash
PYTHONPATH=src python -m subject_evolution.parity \
  --config configs/mvp_short_latent_l2_memory_topk_inherited.json \
  --output runs/parity_v014 \
  --ticks 5 \
  --entities 64 \
  --device-backend auto
```

真实 hybrid world trace：

```bash
PYTHONPATH=src python -m subject_evolution.parity \
  --config configs/mvp_short_latent_l2_memory_topk_inherited.json \
  --output runs/parity_v014_world \
  --ticks 30 \
  --preserve-config-world \
  --world-only \
  --device-backend gpu \
  --require-gpu
```

优先关注首差异：

- requested Top-k capacity；
- selected copy/content IDs 与 score；
- working-memory state；
- L1/L2/knowledge logits；
- routing/selection cost；
- final action、intent、birth/death；
- 持久实体、环境、信息和知识状态。

## 6. 完整 checkpoint 与恢复

配置中启用：

```json
"full_checkpoint_enabled": true
```

运行后会生成 `checkpoint_XXXXXXXX.sechk`。

继续运行：

```bash
PYTHONPATH=src python -m subject_evolution.cli \
  --resume-checkpoint runs/v014_inherited/checkpoint_00000015.sechk \
  --output runs/v014_resumed \
  --until-tick 30 \
  --backend cpu
```

注意：`.sechk` 内含 pickle，只能加载项目自己生成且来源可信的文件。

## 7. 离线配对反事实

工作记忆消融：

```bash
PYTHONPATH=src python -m subject_evolution.replay \
  --checkpoint runs/v014_inherited/checkpoint_00000015.sechk \
  --output runs/ablate_memory \
  --until-tick 30 \
  --intervention ablate-working-memory \
  --backend cpu
```

选择器旁路：

```bash
PYTHONPATH=src python -m subject_evolution.replay \
  --checkpoint runs/v014_inherited/checkpoint_00000015.sechk \
  --output runs/bypass_selection \
  --until-tick 30 \
  --intervention bypass-sparse-selection \
  --backend cpu
```

其他科学干预可通过 `python -m subject_evolution.replay --help` 查看。

## 8. 常用配置

| 配置 | 用途 |
|---|---|
| `smoke_cpu.json` | 最短 CPU 冒烟 |
| `mvp_short_k2_exchange.json` | K2 交换与历史 GPU parity 基线 |
| `mvp_short_k4_candidates.json` | K4 候选图 |
| `mvp_short_replay.json` | 完整 checkpoint/replay |
| `mvp_short_latent_l1_costed.json` | L1 成本路径 |
| `mvp_short_latent_l2_budget_matched.json` | L2 预算匹配 |
| `mvp_short_latent_l2_memory.json` | 工作记忆 |
| `mvp_short_latent_l2_memory_topk4.json` | 固定 Top-k=4 |
| `mvp_short_latent_l2_memory_topk_inherited.json` | v0.14 实体级遗传 Top-k |
| `mvp_small_k2.json` | 较大 500-tick K2 场景，不作为日常测试默认项 |

## 9. 主要输出

- `metrics.csv`：周期指标；
- `summary.json`、`run_metadata.json`：最终摘要；
- `run_manifest.json`：版本、后端和 provenance；
- `scientific_validity.json`：科学有效性标记；
- `resolved_config.json`：实际配置；
- `knowledge_events.jsonl`；
- `knowledge_transfers.csv`；
- `knowledge_outcome_updates.csv`；
- `knowledge_policy_contributions.csv`；
- `knowledge_routing_costs.csv`；
- `knowledge_working_memory.csv`；
- `knowledge_selection_events.csv`；
- `checkpoint_*.npz`：分析快照；
- `checkpoint_*.sechk`：可信完整恢复包。

## 10. 常见故障

### `BackendUnavailableError`

CuPy/CUDA 不可用或不匹配。不要静默回退；先确认设备、驱动和 CuPy 安装。

### CPU/GPU alive 差 1

不要只比较最终 alive。运行 `subject_evolution.parity`，定位首个 tick、阶段、字段和稳定实体 ID。

### `periodic position invariant failed`

v0.6.5 已修复 float32 上界舍入。若再次出现，应检查是否有新代码直接写 `x/y` 而未使用 canonical half-open wrap；错误信息应包含 slot、entity_id 和坐标。

### parity 工具属性错误

不要猜对象字段。曾出现不存在的 `relation_target` 假设；修改 parity 时必须按实际类和 snapshot 结构检查。

### GUI 与 CLI 行为不一致

确认 GUI 使用同一个 `src` 和相同配置。当前 v0.14 项目包不含 GUI wrapper，用户本地 GUI 可能是外部目录。
\newpage

# 版本与 Schema 矩阵


## 1. 核心版本矩阵

| 版本 | Knowledge schema | Policy/Router | 关键能力 |
|---|---|---|---|
| K1/v0.5 | `dynamic-knowledge-k1-v1`（历史） | 原遗传策略 | 副本、容量、成本、交换、损坏 |
| K2/v0.6 | `dynamic-knowledge-k2-v1` | `inherited-linear-policy-v1` | 五维局部后果，不影响策略 |
| K3/v0.7 | K3 知识 | `inherited-linear-policy-knowledge-residual-v1` | 稀疏 outcome residual |
| K4/v0.8 | `dynamic-knowledge-k4-v1` | K3 policy | 内容谱系和候选主体诊断 |
| v0.10 L1 | `dynamic-knowledge-latent-v1` | `quantized-linear-latent-router-v1` | 变长 latent、线性路由 |
| v0.11 L2 | 同上 | `quantized-mlp-latent-router-v1` | 两层 MLP、hard-tanh、L1 shadow |
| v0.12 | 同上 | L1/L2 + `latent-routing-compute-cost-v1` | 真实计算成本和预算 |
| v0.13 | 同上 | L2 + `quantized-working-memory-v1` + `sparse-query-key-topk-router-v1` | 工作记忆、stable Top-k |
| v0.14 | 同上 | v0.13 + `inherited-discrete-topk-v1` | 实体级遗传容量和消融 |

## 2. 基因组隔离

| 路径 | 已知基因组宽度 | 说明 |
|---|---:|---|
| K1/K2 | 136 | 旧策略语义保持 |
| K3 | 142 | 追加五维 outcome preference 和 use strength |
| L1 | 246 | 追加量化线性潜路由 |
| L2 | 446 | 保留 L1 前缀，再追加 MLP 参数 |
| v0.13 memory/top-k | 依配置扩展 | 工作记忆和 Query 参数仅在显式 schema 中追加 |
| v0.14 inherited Top-k | 在 v0.13 基础上追加 1 个容量基因 | 固定 K 配置不追加 |

最后两项的精确总宽度应由当前 `config.py/policy.py` schema 解析结果为准，不要在外部代码中硬编码。

## 3. 当前 v0.14 关键 schema

```text
policy.schema = inherited-variable-latent-router-mlp-v1
knowledge.schema = dynamic-knowledge-latent-v1
latent_schema = variable-latent-knowledge-v1
latent_router_schema = quantized-mlp-latent-router-v1
policy_residual_schema = quantized-variable-latent-mlp-residual-v1
routing_cost_schema = latent-routing-compute-cost-v1
routing_budget_mode = all-or-none-per-entity-v1
working_memory_schema = quantized-working-memory-v1
sparse_selection_schema = sparse-query-key-topk-router-v1
sparse_selection_capacity_schema = inherited-discrete-topk-v1
```

## 4. 兼容性要求

新版本验收至少应比较：

- 非计时 metrics 共同字段；
- 事件/后果/贡献/成本/选择日志共同字段；
- checkpoint 共同数组；
- 基因组旧切片；
- 同 seed 动作、出生死亡和稳定 ID；
- full checkpoint 连续/恢复状态。

## 5. GPU 语义模式

| 模式 | 含义 | 科学状态 |
|---|---|---|
| `strict-reference` | 需要可用 GPU，但世界采用 CPU reference 语义 | 正式正确性门禁 |
| `hybrid-accelerated` | 实验设备世界路径 | v0.14 真实 CUDA parity 待验 |

## 6. Checkpoint schema

完整恢复格式：`subject-evolution-full-checkpoint-v1`，扩展名 `.sechk`。包含 pickle，必须视为可信项目内部文件，不是安全的第三方交换格式。
\newpage

# 新聊天启动提示词


下面的内容可直接复制到新的聊天窗口。建议同时上传：

- `subject_evolution_v014_project.zip`
- 本交接文档包 `subject_evolution_v014_handoff_docs.zip`
- 若要分析实验，再上传 `subject_evolution_v014_results.zip` 或具体 `parity_report.json`

---

我在继续开发一个 Python 演化模拟项目 `Subject Evolution`。当前权威版本是 **v0.14.0**，源码包为 `subject_evolution_v014_project.zip`。请先完整阅读源码包中的：

1. `PROJECT_STATUS.md`
2. `EVOLVABLE_SELECTION_IMPLEMENTATION.md`
3. `CAUSAL_ABLATION_IMPLEMENTATION.md`
4. `CPU_GPU_PARITY.md`
5. `WORKING_MEMORY_IMPLEMENTATION.md`
6. `SPARSE_KNOWLEDGE_SELECTION_IMPLEMENTATION.md`
7. `LATENT_ROUTING_COST_IMPLEMENTATION.md`
8. `LATENT_ROUTER_MLP_IMPLEMENTATION.md`
9. `LATENT_KNOWLEDGE_IMPLEMENTATION.md`
10. `K1_IMPLEMENTATION.md` 到 `K4_IMPLEMENTATION.md`
11. `CHECKPOINT_REPLAY_IMPLEMENTATION.md`
12. `FINAL_TEST_REPORT.txt`

项目当前已实现：

- K1 动态知识内容/副本、容量、成本、交换、损坏和遗忘；
- K2 本地 context/action 的五维后果学习；
- K3 稀疏知识 action-logit residual；
- K4 内容谱系和候选主体图诊断；
- 完整 `.sechk` checkpoint 恢复与离线共同历史反事实；
- 4/8/16/32 维可变长度潜知识；
- L1 量化线性路由和 L2 量化两层 MLP；
- 路由计算成本与 all-or-none 实体能量预算；
- 四维量化工作记忆；
- 无全局类别 embedding、无 Softmax 的 stable Query-Key Top-k 临时工作集；
- 实体级遗传离散 Top-k 容量 `0/1/2/4/8`；
- `ablate-working-memory` 和 `bypass-sparse-selection` checkpoint 干预。

必须保持的科学和工程边界：

- 不引入外部集中训练、global reward、backprop 或未来信息；
- 知识可以使用潜空间和小型路由器，但所有影响必须经过公开 policy residual、成本审核、intent、resolution 和 commit；
- 五维后果不压缩为单一 reward；
- 完整知识权威状态是动态 SoA，Top-k 只是 ephemeral 工作集，不能退化成固定 `K_max` 权威容量；
- 不使用设计者预设的全局类别 embedding 作为控制语义；
- 普通 float Softmax Attention 暂不进入正式路径；
- 新机制必须独立 schema，默认关闭时保持旧配置兼容；
- 新机制必须有成本、贡献日志、checkpoint/replay、单测和短周期对照；
- CPU/GPU 离散动作和稳定 ID 要求逐位一致，不能只接受“小浮点误差”；
- 用户偏好单元测试 + 20-50 ticks 短验证，不要默认反复跑 500 ticks；
- 不要夸大单 seed、短周期结果，不要声称主体性或长期适应优势；
- 当前开发环境没有 CUDA，必须如实说明真实 GPU 未验证范围。

CPU/GPU 历史：K2 hybrid 路径已由用户在真实 GPU 上运行至 tick 1000，无偏差；v0.14 的 latent L2、工作记忆、Top-k、遗传容量和成本尚未完成真实 CUDA world parity。正式 GPU 默认是 `strict-reference`，`hybrid-accelerated` 为实验路径。

历史重要 bug，避免重复：

- parity 工具曾凭空假设 `relation_target` 属性；必须读真实类结构；
- NumPy/CuPy FP32 `reduceat` 归约顺序导致信息/资源持久场分歧；
- float32 周期取模可能返回精确上界；
- hybrid GPU 曾漏传 knowledge policy plan；
- 潜长度变体必须在容量/传输审核前预演目标字节；
- 实体级 selection 工作量不能按 nonzero action 重复累计。

当前测试状态：64 tests，63 passed，1 个真实 CUDA 测试 skip。固定 K 的 v0.13/v0.14 共同状态兼容；遗传容量双重复确定。

建议下一步优先级：

1. 在真实 GPU 上运行 `subject_evolution.parity`，验证 v0.14 requested capacity、selected IDs/scores、working memory、L2 residual、成本、action 和完整 world checkpoint；
2. 若失败，只根据首个差异修复，不根据最终 alive 猜测；
3. 若通过，建立多 seed、多 intervention tick 的 memory/selection 因果矩阵；
4. 再考虑单内容/单谱系消融或局部可塑性。

请直接执行任务，不要重复询问已经在文件或本提示中提供的信息。对复杂任务给简短进度更新；如无法完成某硬件验证，要明确说出限制并交付可在目标主机运行的诊断工具。

---
\newpage

# 交付物索引


## 1. 顶层交付

| 文件 | 说明 |
|---|---|
| `subject_evolution_v014_project.zip` | v0.14.0 源码、配置、测试和报告 |
| `subject_evolution_v014_project.tar.gz` | 同一源码的 TAR.GZ |
| `subject_evolution_v014_results.zip` | v0.14 短实验、消融结果和日志 |
| `subject_evolution_v014_results.tar.gz` | 同一结果的 TAR.GZ |
| `subject_evolution_v014.patch` | v0.13 -> v0.14 差异补丁 |
| `subject_evolution_v014_SHA256SUMS.txt` | 原交付哈希 |

## 2. 当前状态和入口

| 文件 | 用途 |
|---|---|
| `PROJECT_STATUS.md` | 当前已完成/未完成与下一步 |
| `SPLIT_MANIFEST.md` | 模块拆分和各版本新增文件 |
| `FINAL_TEST_REPORT.txt` | 最终单元测试明细 |
| `pyproject.toml` | 包版本、Python 和依赖 |

## 3. 当前阶段报告

| 文件 | 用途 |
|---|---|
| `EVOLVABLE_SELECTION_IMPLEMENTATION.md` | v0.14 遗传 Top-k 容量设计 |
| `EVOLVABLE_SELECTION_CONTROL_MATRIX_REPORT.md` | 固定 K/遗传 K 短对照与消融摘要 |
| `EVOLVABLE_SELECTION_VALIDATION_REPORT.json` | 机器可读 v0.14 验证 |
| `CAUSAL_ABLATION_IMPLEMENTATION.md` | 记忆消融和选择器旁路语义 |
| `V013_V014_COMPATIBILITY_REPORT.json` | 固定 K 兼容性 |

## 4. 历史阶段实现说明

- `K1_IMPLEMENTATION.md`
- `K2_IMPLEMENTATION.md`
- `K3_IMPLEMENTATION.md`
- `K4_IMPLEMENTATION.md`
- `CHECKPOINT_REPLAY_IMPLEMENTATION.md`
- `LATENT_KNOWLEDGE_IMPLEMENTATION.md`
- `LATENT_ROUTER_MLP_IMPLEMENTATION.md`
- `LATENT_ROUTING_COST_IMPLEMENTATION.md`
- `WORKING_MEMORY_IMPLEMENTATION.md`
- `SPARSE_KNOWLEDGE_SELECTION_IMPLEMENTATION.md`
- `CPU_GPU_PARITY.md`
- `PERIODIC_POSITION_FIX.md`

## 5. 关键源码

| 文件 | 说明 |
|---|---|
| `simulation.py` | 世界主循环和阶段提交 |
| `knowledge.py` | K1/K2 知识权威状态和事件 |
| `knowledge_policy.py` | K3 和潜路由的稀疏策略计划 |
| `knowledge_subjects.py` | K4 候选主体诊断 |
| `latent_knowledge.py` | 变长潜内容、L1/L2、Top-k 和容量解析 |
| `working_memory.py` | 定点工作记忆 |
| `routing_cost.py` | 计算成本和预算仲裁 |
| `checkpointing.py` | `.sechk` |
| `replay.py` | 离线恢复/分支 CLI |
| `interventions.py` | 科学干预 |
| `parity.py` | CPU/GPU 首差异定位 |
| `gpu_runtime.py` | hybrid 设备路径 |

## 6. 关键配置

- `configs/mvp_short_latent_l2_memory_topk_inherited.json`：v0.14 当前最高能力短配置；
- `configs/mvp_short_latent_l2_memory_topk4.json`：固定 K=4 兼容基线；
- `configs/mvp_short_latent_l2_budget_matched.json`：L2 预算匹配；
- `configs/mvp_short_replay.json`：完整 checkpoint；
- `configs/mvp_short_k4_candidates.json`：K4；
- `configs/mvp_short_k2_exchange.json`：K2 交换和历史真实 GPU parity；
- `configs/mvp_small_k2.json`：较大 K2 场景。

## 7. 结果目录样例

`subject_evolution_v014_results/runs/inherited_a/` 和 `inherited_b/` 是 v0.14 双重复。`ablate_memory/` 与 `bypass_selection/` 为 checkpoint 分支结果。

## 8. 本交接包

- `00_README_FIRST_CN.md`
- `01_PROJECT_OVERVIEW_CN.md`
- `02_PROJECT_PROGRESS_CN.md`
- `03_ARCHITECTURE_AND_SCIENCE_BOUNDARIES_CN.md`
- `04_RUNBOOK_CN.md`
- `05_HANDOFF_REPORT_CN.md`
- `06_NEW_CHAT_BOOTSTRAP_PROMPT_CN.md`
- `07_ARTIFACT_INDEX_CN.md`
- `08_VERSION_AND_SCHEMA_MATRIX_CN.md`
- `PROJECT_HANDOFF_PACKAGE_CN.docx`
- `PROJECT_HANDOFF_PACKAGE_CN.pdf`
