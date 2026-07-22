# v0.4 GPU 混合执行阶段

本阶段将已对照的 GPU 基础层接入运行时：无状态随机键、环境/信息场、规则网格、观察构建、参数化策略批处理和采集冲突计划。`--backend gpu` 是显式的混合模式：CPU 保留语义权威的世界提交，GPU 承担规模化数组计算。它不是“悄悄回退”的自动优化，也不是完整设备驻留世界循环。

## 后端选择

GPU实现以可选的 CuPy 后端提供。没有安装 CuPy 或没有可用 CUDA 设备时：

- `cpu` 后端继续使用 NumPy；
- `auto` 后端安全回退到 NumPy；
- 明确要求 `gpu` 时给出可操作的错误，而不是悄悄改变实验模式。

这避免在 CPU/GPU 对照实验中误把回退执行当作 GPU 结果。

安装时应选择与目标 CUDA Toolkit **主版本**匹配的 **CuPy ≥ 12** Conda 包或 wheel；项目不把某个 CUDA 版本硬编码为强制依赖。CUDA 13.x 使用 `cupy-cuda13x`，CUDA 12.x 使用 `cupy-cuda12x`，且两种 CuPy wheel 不能并存。该版本要求保证严格阶段所需的 `lexsort` 和 `ufunc.reduceat` 可用。

在本工作区的 WSL2 / CUDA Toolkit 13.3 环境中，需先使动态链接器能定位 Toolkit：

```bash
conda activate se
python -m pip install -U cupy-cuda13x
export CUDA_PATH=/usr/local/cuda-13.3
export CUDA_HOME="$CUDA_PATH"
export LD_LIBRARY_PATH="$CUDA_PATH/targets/x86_64-linux/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
```

若 CUDA 安装位置不同，改用该位置；建议将变量放入 `se` 环境的激活脚本。CPU 模式不依赖这些变量。

## 已迁移语义

| 阶段 | GPU组件 | 对照规则 |
|---|---|---|
| 1 | 无状态键、Uniform、Bernoulli、Normal、Categorical | 相同随机键应给出相同离散结果；浮点分布按容差比较 |
| 2 | 四资源场、危险场、三通道信息场 | 固定配置和 tick 下比较字段、年龄及采集分配 |
| 3 | cell ID、稳定排序、cell 边界、局部伙伴采样 | 稳定 ID 不变；固定种子下伙伴槽位一致 |
| 4 | 场/伙伴观察、感知噪声、信息分类 | 观察 schema 不变；CPU 固定槽与 GPU 紧凑槽均消费同一个稀疏 `DirectMessageObservationPlan` |
| 5 | 参数化策略、动作采样与方向选择 | 相同种子小场景动作一致；浮点状态按容差比较 |
| 6（采集子集） | `GpuActionConflictResolver` 的采集行定位、`(cell_id, entity_id)` 稳定排序和公平分配 | 只读快照输入、返回主机 `HarvestResolution`；资源仍只在统一提交阶段扣减 |
| 7（CPU计划边界） | `ShareResolution → RelationUpdatePlan` | 后端无关、规范事件顺序；固定关系槽仍由 CPU 提交 |
| 8（CPU计划边界） | `BirthRequestPlan → BirthAllocationPlan`、`DeathEventPlan` | 槽池版本和稳定 ID 固定计划快照；死亡先记录事件、主体图更新后再统一回收槽位 |
| 8.5（观察边界） | `DirectMessageObservationPlan`、整步传输计数 | CPU 保留固定注意力槽；GPU 仅上传实际事件并只为实际接收者保留原容量归约宽度 |

所有高竞争字段写入采用稳定 `(cell_id, 原始顺序)` 排序和分段归约。每个 cell 最后只写一次，避免 GPU 浮点 `atomicAdd` 的非确定累加顺序。信号发射以 `SignalEmissionPlan` 的有序单通道批次提交：高频事件可以追加到低频**目标通道**的待发队列；到期时该通道按到达顺序合并为一次传输与严格归约。未到期通道不会创建零填充列，也不会跨越主机/设备边界。默认 `[1,1,1]` 是无队列直通，字段扩散/衰减仍每 tick 执行；较长周期是显式信号交付延迟，而非隐式跳过字段更新。

GPU 的 SplitMix64 键生成使用单个 CuPy 元素核融合上下文混合、draw index 和最终器；其 `uint64` 输出由 GPU/CPU 位级测试固定。设备观察和策略调用的概率、标准差和动作 mask 都已由配置或前置计算保证有效，因此内部调用避免重复的主机同步校验；公共采样 API 默认仍执行输入校验。

GPU数组仅包含原本的世界字段。策略仍只读取既有观察结构，不能读取 cell 排序、中间归约或设备诊断数据。

## 混合边界

设备侧：环境与信息场更新、信号场发射、采集计划（稳定键排序与公平分配）、采集提交、规则网格、伙伴采样、场与伙伴观察、策略 logits/采样/方向。

CPU侧：延迟消息队列的所有权及批量解码、行动意图、位置/能量提交、分享/关系事件计划与固定槽应用、生命周期提交、群体识别、主体图、CSV 和检查点。直接消息以 NumPy 数组批次排队并形成规范稀疏 `DirectMessageObservationPlan`；CPU 参考可按需物化 `active × capacity` 固定槽，GPU 当前只上传 receiver row、slot 和 payload，在设备上为实际接收者构造紧凑固定槽。分享结算输出自包含 `ShareResolution`，关系事件以规范 `RelationUpdatePlan` 按拥有者局部顺序分轮提交。繁殖接受输出带父实体/主体来源的 `BirthRequestPlan`，版本化槽池生成确定的 `BirthAllocationPlan`；死亡在主体失活和槽位回收前生成带组合死因与最终状态的 `DeathEventPlan`。仅回传 CPU 提交实际需要的动作和观察摘要，资源梯度只在群体更新 tick 回传。稳定 ID、基因型和低频群体字段缓存在设备；批量 `run()` 在结束前才同步完整字段镜像。

行动冲突不属于某个设备后端：`execution.py` 接收只读 `ActionResolutionSnapshot` 和意图批次，输出不修改世界的 `ActionResolutionPlan`。CPU 运行使用严格 CPU 排序；GPU 运行默认以 `GpuActionConflictResolver` 仅替换采集子计划，并继续复用 CPU 的分享和繁殖规则。`run.gpu_harvest_conflict_planner=false` 可切回 CPU 键构建以做部署剖析；两条路径都只返回计划，世界提交仍只接受计划中的 `ActionResolutionBatch`。移动目前没有共享冲突，仍作为成功意图在统一 CPU 提交中更新位置，不会伪装成设备世界写入。

控制仲裁同样独立于设备后端：`control.py` 先记录控制来源、承载体和策略决策，再由仲裁器生成可进入意图阶段的单一决策。意图可保留完整贡献主体与权重。当前身体策略走单提案快速路径；社会、谱系、制度、Hero/RL 或外部控制器可以实现加权、优先级、否决或竞价仲裁，但不能跳过意图/解析/提交边界。

`control.heuristic_social_guidance` 是默认关闭以保持基线可比性的社会方向控制规则。启用时，CPU 控制边界使用已有的低频社会方向和稳定社会主体 ID，为已采样的资源移动混合方向；它不重采样动作、不读取 GPU 内部真值，也不增加设备字段或观察回传。`run_metadata.json` 和可选轨迹都会标记该规则及其实际应用次数。方向混合是模型启发式而非因果控制/主体性证明，GPU 与 CPU 的对照实验必须按此开关分开报告。

关系状态仍由 CPU 持有，但不再在每个 tick 对完整固定槽位表做衰减或死链接扫描。分享写入与低频群体检测是关系值的消费边界：系统在那里按累计 tick 数物化几何衰减；只有发生死亡时才清理死目标。该优化不让 GPU 策略读取关系内部真值，也不改变 `Snapshot → Plan → Commit` 的提交边界。

`step_seconds` 是世界 step 本身；`window_seconds_per_tick` 统计上一个报告窗口内的墙钟平均，包含日志和检查点等非 step 工作。应使用后者和 `run_metadata.json` 的 `wall_seconds` 判断实际吞吐。`gpu_h2d_bytes`、`gpu_d2h_bytes` 统计一个 step 在运行时显式边界上传输的数组 payload；`gpu_direct_message_events` 和 `gpu_direct_dense_bytes_avoided` 分别记录稀疏接受事件及相对旧固定全表规避的主机上传字节，不包含 CUDA 驱动协议开销。

## 验证方式

测试套件始终运行 NumPy 对照；检测到可用 CuPy 时还会运行 GPU 对照。建议在目标设备上执行：

```bash
conda activate se
export CUDA_PATH=/usr/local/cuda-13.3
export CUDA_HOME="$CUDA_PATH"
export LD_LIBRARY_PATH="$CUDA_PATH/targets/x86_64-linux/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
python -m pytest -q
```

对环境、信息场和资源提交的独立性能/一致性检查：

```bash
python scripts/verify_gpu_foundation.py --config configs/mvp_small.json
```

运行完整 GPU 路径：

```bash
python -m subject_evolution.cli \
  --config configs/mvp_100k.json \
  --output runs/mvp_100k_gpu \
  --backend gpu
```

本工作区已在 WSL2、NVIDIA GeForce RTX 4070、CUDA Toolkit 13.3 和 `cupy-cuda13x==14.1.1` 上验证：完整测试套件为 `61 passed`。三步 CPU/GPU 同种子场景动作计数一致，字段状态只存在小的 FP32 容差；`--ticks 16` 的字段最大绝对误差为 `2.12e-6`，小于 `5e-6` 容差。新增采集计划测试逐项比较稳定行/单元顺序、分配和失败码，并断言设备资源在计划阶段不变；GPU 克隆测试还确认反事实分支重绑定自己的设备运行时。关系维护优化的已预热单 step `cProfile` 由约 `0.112秒` 降至 `0.077秒`；融合随机键使同一剖析中随机相关累计时间从约 `18ms` 降至 `6ms`。三通道稠密共享排序虽然在 131,072 事件微基准中为 `3.19×`，但 300 tick 端到端运行没有提升，且会阻碍异频通道；默认运行时因此采用稀疏、有序的发射计划。默认 `[1,1,1]` cadence 是不入队的直通快路径；`(1,3,2)` 异频 cadence 的端到端 CPU/GPU 对照也已通过。阶段 8.5 的 100,000 实体、300 tick 严格 GPU 两次为 `25.55/27.14秒`，相对阶段 8 最快 `30.95秒` 改善约 `12.3%–17.4%`；action counts 和最终离散状态均保持一致。部署仍应按自身负载复测。字段和策略观察当前仍固定为三通道。每通道传播频率或可变通道数必须作为显式模型配置实现，不能由调度器隐式跳过。

下一步进入群体标签传播：先建立只读关系/活动实体快照，再生成标签/成员分段计划，最后由主体图单写者提交节点、边和增量 summary；完成 CPU 计划对照后再评估关系槽、标签数组与生命周期 SoA 的联合设备驻留。
