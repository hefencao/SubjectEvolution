# Subject Evolution 项目进度与版本演进

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
