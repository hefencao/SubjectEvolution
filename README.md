# 嵌套主体存在演化模拟：v0.4 GPU 混合执行阶段

这是项目规范的可运行 CPU 参考内核和分阶段 GPU 实现。v0.4 将字段、规则网格、观察构建、演化策略批处理和采集冲突子计划接入显式 GPU 路径；GPU 模式的环境/信息场在设备上权威演进，实体、关系、出生死亡与主体图当前仍由 CPU 提交。分享关系与生命周期已经使用后端无关的只读计划/事件合约，为后续设备驻留或分布式实现保留同一提交边界，而不把 CPU 固化为永久唯一写者。

## 已实现

- 圆球物理承载体与身体、谱系、社会候选主体的概念分离；
- 固定容量SoA实体状态；
- 二维周期世界与四类不可完全替代资源；
- 季节变化、危险场和三通道信息场；
- 相邻网格局部伙伴采样，无全体两两搜索；
- 无状态随机键及统一Bernoulli、Normal、Categorical采样；
- 可选 CuPy 后端：GPU 数组上的无状态随机键和基础分布；
- GPU 无状态随机键使用融合的 uint64 SplitMix64 元素核，仍与 CPU 键流逐位一致；
- 设备版四资源环境、危险场、三通道信息场、规则网格和伙伴采样；
- `--backend gpu` 混合运行：设备权威字段、伙伴采样、场/伙伴观察、策略批处理和只读采集冲突计划；
- GPU 混合路径使用版本化 `DeviceEntityState` 持久保存观察字段；CPU 最终提交通过密度感知 `EntityDeviceCommitPlan` 同步，高密度连续复制、低密度稀疏补丁，批量 `run()` 在结束时同步环境/信息字段镜像；
- 延迟直接消息队列以数组批次保存；接收使用批量随机键、稳定排序和向量化容量分配，并输出后端无关的稀疏 `DirectMessageObservationPlan`；CPU 可按需物化固定注意力槽，GPU 仅为实际接收者构造紧凑槽张量；
- 场发射与资源提交使用稳定排序、分段归约，不依赖浮点原子累加；信号发射通过按通道有序的 `SignalEmissionPlan` 提交，未到期通道不生成或传输零值；
- 传播丢失、接收噪声、语义误分类和伙伴感知误差；
- 演化策略基因组：8 种行动对 16 类约束观察特征的 128 个偏好权重全部由初始受限随机生成、亲代继承和稀疏突变产生，策略代码不再写入行动偏好系数；突变发生率与条件幅度分离，默认每基因 1%；
- 控制提案—仲裁—意图边界：身体、社会、谱系、制度、Hero 或外部控制器可共享同一仲裁接口，不能直接写世界；意图可审计主控制来源及逐贡献者主体 ID、控制器类型和权重；
- 可配置的社会方向控制：只允许在 `entertainment` 协议显式启用，候选社会主体对既有资源移动方向做加权引导并记录来源；
- 娱乐版独立觅食替换模块：按稳定 ID 抽取队列并直接替换部分行动；科学协议在代码层拒绝该模块，输出也会标记 `direct-action`，不能作为自主性或主体偏移证据；
- 行动采样、移动、采集、分享、发信号、繁殖和逃离；
- 行动提案、稳定意图ID、资源/分享/出生冲突的统一结算和执行记录；
- 后端无关的冲突解析协议：只读快照产生 `ActionResolutionPlan`，世界提交始终只读取已解析结果；
- 分享结算产生自包含 `ShareResolution` 和规范排序的 `RelationUpdatePlan`；关系事件保留来源意图、正反向标记与 tick，提交不依赖隐式上一阶段状态；
- 繁殖结算产生带父实体/主体来源的 `BirthRequestPlan`，版本化空闲槽池生成确定的 `BirthAllocationPlan`；死亡在回收槽位前形成含组合死因和最终状态的 `DeathEventPlan`；
- 区域信号场与固定容量、带延迟的点对点消息队列；
- 固定容量信任关系；分享事件按拥有者局部顺序分轮批处理；
- 关系信任/熟悉度在分享写入或群体检测读取时按精确几何规则物化；无事件 tick 不再扫描整张关系表；
- 基于高信任关系的社会群体候选识别；只读 `GroupDetectionSnapshot` 由可插拔规划器生成规范 `GroupLabelPlan`，社会状态和主体图分别提交；
- 群体资源方向形成对成员行动的高层影响；
- 谱系继承、变异、出生、死亡和容量管理；
- 社会依赖代理指标、群体指标、原始策略权重、信息检测率、行动熵，以及逐 step 的利益边界流、显式 H2D/D2H、实体提交字节/耗时和稠密消息字节规避统计；
- 每 500 tick 独立输出世代深度、有效谱系、去 softmax 共同偏移的策略多样性、固定探针行为差异和窗口行动分布；
- 身体、谱系和社会候选主体图，以及主体ID和实体ID的显式分离；群体成员一次分段提交，活跃类型摘要增量维护，社会节点累计内部利益和跨边界流；
- 类型化的成对反事实分支：记录修改存在、修改环境、修改规则等干预类别、目标范围和是否直接控制；引入新存在的接口类别已预留，具体可复制信息存在尚未实现；
- 检查点、CSV指标、运行元数据和基础测试。

## 尚未实现

- 完整设备驻留世界循环（行动结算、关系、出生死亡、主体图和日志仍在 CPU）；
- 完整主体图数据库及任意嵌套主体；
- 离线反事实分支重放；
- 信息模板寄生主体；
- 完整主体性评分；
- 动态知识副本、局部后果学习与有代价知识交换；
- Hero强化学习；
- 可视化客户端；
- 多GPU。
- 可配置的任意信息通道 schema（当前资源、危险、社会三类通道仍固定）。

这些接口已在数据分层中预留，不需要让策略直接访问世界对象。

## 安装

```bash
cd subject_evolution_mvp
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

GPU 基础阶段需要与已安装 CUDA Toolkit 的**主版本**匹配的 **CuPy ≥ 12** 包。CUDA 13.x 应安装 `cupy-cuda13x`，CUDA 12.x 应安装 `cupy-cuda12x`；两者不能同时安装。未安装 CuPy 或无 GPU 时，CPU 参考实现与全部非 GPU 测试照常可用。

本工作区的 WSL2 + CUDA Toolkit 13.3 环境可按以下方式配置：

```bash
conda activate se
python -m pip install -U cupy-cuda13x
export CUDA_PATH=/usr/local/cuda-13.3
export CUDA_HOME="$CUDA_PATH"
export LD_LIBRARY_PATH="$CUDA_PATH/targets/x86_64-linux/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
python -m pytest -q
```

若系统的 CUDA 安装目录不同，请把 `CUDA_PATH` 改为实际路径。上述变量让 CuPy 在 WSL 中定位工具包和动态库；`CUDA_HOME` 应与 `CUDA_PATH` 相同，避免 Conda 遗留值导致的运行时告警。可将它们写入 Conda 环境激活脚本以免每次重复设置。

开发测试：

```bash
pip install -e '.[dev]'
pytest
```

## 运行小型演示

```bash
python -m subject_evolution.cli \
  --config configs/mvp_small.json \
  --output runs/demo_gpu \
  --backend gpu
```

运行成对反事实分支：

```bash
python -m subject_evolution.cli \
  --config configs/mvp_small.json \
  --output runs/social_control_off \
  --counterfactual reverse-environment \
  --intervention-tick 100
```

该命令先演进 100 tick 共享前史，再从同一内存快照分出`baseline/`和`intervention/`，并在根目录写入含干预前锚点的`counterfactual_summary.json`。省略`--intervention-tick`时保持 tick 0 立即干预。当前`reverse-environment`将资源与危险地理旋转 180°，且后续季节危险更新保持该朝向；这是 M4 环境反转的可复现实例化，不排除未来增加其他反转算子。

运行娱乐版“共同社会切断 → 切断对照/直接行动替换”演示：

```bash
python -m subject_evolution.cli \
  --config configs/mvp_small.json \
  --output runs/foraging_override \
  --backend gpu \
  --experiment-mode entertainment \
  --shared-intervention cut-social-connections \
  --shared-intervention-tick 100 \
  --counterfactual independent-foraging-override \
  --intervention-tick 150
```

队列在分支点按稳定实体 ID 和无状态随机键精确抽取。两分支跟踪相同队列，只有处理分支启用 `independent-foraging-v1`。这是直接覆盖行动的娱乐/演示机制，不属于基础实验或科学干预；默认 `scientific` 模式会拒绝运行它。实验边界见 [实验协议](docs/EXPERIMENT_PROTOCOL.md)，未决问题见 [科学问题与研究债务](docs/SCIENTIFIC_ISSUES.md)，知识分层的实施边界见 [知识架构评估](docs/KNOWLEDGE_ARCHITECTURE.md)。

输出：

- `metrics.csv`：周期指标；除阶段墙钟外，还包含原始策略权重、利益边界流以及娱乐模块的隔离指标；即使总 tick 不整除报告周期，也会写入最后一条最终指标；
- `evolution_progress.jsonl`：默认每 500 tick 的独立演化诊断；原始权重、规范策略、固定探针行为、世代和谱系指标必须联合解释；
- `summary.json`：最后一条指标；
- `run_metadata.json`：运行时间、累计动作、实验协议和结构化科学有效性审计；
- `checkpoint_*.npz`：抽样检查点；
- `config.json`：实际运行配置副本。

## 运行10万实体配置

```bash
python -m subject_evolution.cli \
  --config configs/mvp_100k.json \
  --output runs/mvp_100k_gpu \
  --backend gpu
```

不带 `--backend` 时仍是严格 CPU 参考路径。`--backend gpu` 会明确启用混合 GPU 路径；`--backend auto` 仅在 GPU 可用时使用它，否则回退 CPU。GPU 路径默认以 `GpuActionConflictResolver` 在设备上构建采集子计划：它只读取 `ActionResolutionSnapshot` 并返回稳定排序的计划；随后资源由设备字段提交器修改，实体结果由当前 CPU 提交器修改。10万实体应使用独立输出目录，避免同目录混入不同后端或中断运行的检查点。

若需和旧的“CPU 构建采集键、GPU 分配资源”路径做性能剖析，可在 `run` 中明确关闭该执行优化；这不改变模型、随机键或提交顺序：

```json
"gpu_harvest_conflict_planner": false
```

在有 CUDA 的机器上，先对已迁移阶段运行对照：

```bash
conda activate se
export CUDA_PATH=/usr/local/cuda-13.3
export CUDA_HOME="$CUDA_PATH"
export LD_LIBRARY_PATH="$CUDA_PATH/targets/x86_64-linux/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
python scripts/verify_gpu_foundation.py --config configs/mvp_small.json
```

## 基础实验协议

基础实验默认使用 `run.experiment_mode="scientific"`。此协议允许代码固定物理行动语义、可行性 mask、传感特征、遗传/突变机制和候选主体的测量规则，但不允许固定行动偏好或在采样后替换行动。初代策略权重是在边界约束内按稳定随机键生成的数据，后代只通过继承与突变取得策略；有限记忆来自观察更新。`run_metadata.json.scientific_validity` 会给出结构来源、固定约束、违规项以及该运行是否属于未干预严格基线。该结构审计只证明实现没有越过声明边界，不替代多种子、预注册假设和统计检验。

干预的实现优先级目前低于基础演化。注册层仍区分 `introduce-existence`、`modify-existence`、`modify-environment`、`modify-rules` 和娱乐专用的 `direct-action`，以便未来加入会自行复制、变异并通过既有观察通道影响承载体的信息/模因存在，而无需扩张为外部行动控制器。

## 信息场交付 cadence

`information.signal_flush_periods` 为当前资源、危险、社会三个字段通道分别指定正整数交付周期，默认 `[1, 1, 1]` 保持逐 step 发射。周期大于 1 时，事件会在 CPU 调度器中按通道累积，并只在该通道的到期 step 作为一个稀疏批次提交；字段传播仍逐 step 运行，直接消息也不受此配置影响。因此它是显式的模型时间聚合规则，而不是跳过低频字段计算的性能开关。

## 随机键

每个随机结果由以下字段决定：

```text
run_seed, tick, simulation_phase, subject_id, stream_id, draw_index
```

因此主体数组顺序变化或增加无关日志不会改变既有主体的随机序列。

## 当前社会主体实现

社会群体不是预先指定的奖励对象。高信任关系形成局部连通结构后，系统将其识别为候选群体，并计算群体的平均资源方向。该方向是可观察输入和行动语义的一部分；个体是否选择、以及如何权衡相关行动，由遗传策略矩阵与当时观察共同产生。

## 社会方向引导（可配置建模规则）

`control.heuristic_social_guidance` 默认是 `false`；启用时还必须把 `run.experiment_mode` 设为 `entertainment`。候选社会主体会以其稳定主体 ID 提交方向提案，仲裁器对身体策略已采样的 `MOVE_RESOURCE` 方向做加权混合。该机制不会改变动作类别或随机键，但会直接修改方向，因而不进入严格基础实验。

方向混合是明确记录的建模启发式，而不是主体性评分、因果归因或社会决策理论的证明。`run_metadata.json` 会记录配置、仲裁器名称和实际受引导行动数；若启用轨迹记录，`trajectory.jsonl` 还会写入 `heuristic_control`、全部贡献主体 ID 和贡献权重。关闭该选项时，默认单身体提案路径、随机流和 GPU 数据边界保持不变。

例如，在实验配置中显式启用：

```json
"control": {
  "heuristic_social_guidance": true,
  "heuristic_social_guidance_weight": 0.25
},
"run": { "experiment_mode": "entertainment" }
```

## 架构入口

- `random_api.py`：统一采样；
- `backend.py`：可选 NumPy/CuPy 后端与显式主机/设备转换；
- `gpu_environment.py`：设备版环境与信息场阶段；
- `gpu_runtime.py`：GPU 观察/策略、设备字段提交与主机提交之间的显式边界；
- `device_state.py`：持久设备实体镜像的版本化、密度感知最终状态计划；
- `execution.py`：只读 `ActionResolutionSnapshot`、可审计计划和 CPU/GPU 采集解析器；
- `lifecycle.py`：后端无关的出生请求/槽位分配与死亡事件计划；
- `spatial.py`：空间索引与局部伙伴采样；
- `information.py`：传播、接收误差、稀疏直接消息观察计划和固定槽按需物化；
- `policy.py`：约束特征/行动语义与可遗传策略权重分离的演化策略实现；
- `evolution.py`：固定 cadence 的谱系、规范策略和探针行为诊断；
- `interventions.py`：干预类别、目标范围及科学/娱乐协议边界；
- `control.py`：控制提案、仲裁协议、完整贡献来源审计和可选启发式社会引导；
- `SCIENTIFIC_ISSUES.md`：高价值未决问题、解释边界和执行条件；
- `KNOWLEDGE_ARCHITECTURE.md`：动态知识副本、局部后果学习和有代价交换的分阶段评估；
- `social.py`：可回放关系事件计划、固定槽关系和候选群体；
- `subjects.py`：候选主体节点、历史边与规范群体成员分段提交；
- `simulation.py`：阶段化世界执行；
- `environment.py`：资源、气候和危险。

## 批量实验

```bash
python scripts/run_sweep.py --output runs/sweep --ticks 200 --seeds 3
```

该脚本比较低噪声/低温、基线和高噪声/高温条件，并输出`sweep_summary.csv`。

## 设计文档

- `docs/IMPLEMENTATION_STATUS.md`：v0.4完成度、实测规模与已知简化；
- `docs/GPU_FOUNDATION.md`：GPU 混合执行、对照语义与运行要求；
- `docs/NEXT_GPU_PHASE.md`：GPU迁移顺序；
- `docs/specification/`：项目总规范和四份工程规范。
