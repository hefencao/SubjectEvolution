# Subject Evolution 项目说明（v0.14.0）

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
