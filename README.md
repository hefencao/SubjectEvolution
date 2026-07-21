# 嵌套主体存在演化模拟：v0.4 GPU 混合执行阶段

这是项目规范的可运行 CPU 参考内核和分阶段 GPU 实现。v0.4 将字段、规则网格、观察构建和参数化策略批处理接入显式 GPU 路径；行动结算、关系、出生死亡与主体图仍由 CPU 保持语义权威。

## 已实现

- 圆球物理承载体与身体、谱系、社会候选主体的概念分离；
- 固定容量SoA实体状态；
- 二维周期世界与四类不可完全替代资源；
- 季节变化、危险场和三通道信息场；
- 相邻网格局部伙伴采样，无全体两两搜索；
- 无状态随机键及统一Bernoulli、Normal、Categorical采样；
- 可选 CuPy 后端：GPU 数组上的无状态随机键和基础分布；
- 设备版四资源环境、危险场、三通道信息场、规则网格和伙伴采样；
- `--backend gpu` 混合运行：设备字段、伙伴采样、场/伙伴观察和策略批处理；
- GPU 混合路径只回传 CPU 提交实际所需的结果；稳定ID、基因型和低频群体状态在设备缓存，批量 `run()` 在结束时同步字段镜像；
- 延迟直接消息队列以数组批次保存；接收使用批量随机键、稳定排序和向量化容量分配，不再逐条创建/处理 Python 消息对象；
- 场发射与资源提交使用稳定排序、分段归约，不依赖浮点原子累加；
- 传播丢失、接收噪声、语义误分类和伙伴感知误差；
- 参数化共享策略、个体遗传潜变量和有限记忆；
- 控制提案—仲裁—意图边界：身体、社会、谱系、制度、Hero 或外部控制器可共享同一仲裁接口，不能直接写世界；意图可审计主控制来源及完整贡献者/权重；
- 可配置的社会方向控制：显式启用后，候选社会主体仅对既有资源移动方向做加权引导；默认关闭以保持基线可比，并在输出中记录其建模启发式；
- 行动采样、移动、采集、分享、发信号、繁殖和逃离；
- 行动提案、稳定意图ID、资源/分享/出生冲突的统一结算和执行记录；
- 后端无关的冲突解析协议：只读快照产生 `ActionResolutionPlan`，世界提交始终只读取已解析结果；
- 区域信号场与固定容量、带延迟的点对点消息队列；
- 固定容量信任关系；分享事件按拥有者局部顺序分轮批处理；
- 关系信任/熟悉度在分享写入或群体检测读取时按精确几何规则物化；无事件 tick 不再扫描整张关系表；
- 基于高信任关系的社会群体候选识别；
- 群体资源方向形成对成员行动的高层影响；
- 谱系继承、变异、出生、死亡和容量管理；
- 社会依赖代理指标、群体指标、信息检测率和行动熵；
- 身体、谱系和社会候选主体图，以及主体ID和实体ID的显式分离；
- 成对随机的反事实分支：关闭社会控制、切断社会连接、打乱记忆或冻结遗传；
- 检查点、CSV指标、运行元数据和基础测试。

## 尚未实现

- 完整设备驻留世界循环（行动结算、关系、出生死亡、主体图和日志仍在 CPU）；
- 完整主体图数据库及任意嵌套主体；
- 离线反事实分支重放；
- 信息模板寄生主体；
- 完整主体性评分；
- Hero强化学习；
- 可视化客户端；
- 多GPU。

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
  --counterfactual disable-social-control
```

该命令在`baseline/`和`intervention/`中写入两条轨迹，并在根目录写入`counterfactual_summary.json`。两条分支从同一快照和随机键规则开始。

输出：

- `metrics.csv`：周期指标；`step_seconds` 仅覆盖世界 step，`window_seconds_per_tick` 是包含前一窗口日志/检查点开销的墙钟平均；即使总 tick 不整除报告周期，也会写入最后一条最终指标；
- `summary.json`：最后一条指标；
- `run_metadata.json`：运行时间和累计动作；
- `checkpoint_*.npz`：抽样检查点；
- `config.json`：实际运行配置副本。

## 运行10万实体配置

```bash
python -m subject_evolution.cli \
  --config configs/mvp_100k.json \
  --output runs/mvp_100k_gpu \
  --backend gpu
```

不带 `--backend` 时仍是严格 CPU 参考路径。`--backend gpu` 会明确启用混合 GPU 路径；`--backend auto` 仅在 GPU 可用时使用它，否则回退 CPU。10万实体应使用独立输出目录，避免同目录混入不同后端或中断运行的检查点。

在有 CUDA 的机器上，先对已迁移阶段运行对照：

```bash
conda activate se
export CUDA_PATH=/usr/local/cuda-13.3
export CUDA_HOME="$CUDA_PATH"
export LD_LIBRARY_PATH="$CUDA_PATH/targets/x86_64-linux/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
python scripts/verify_gpu_foundation.py --config configs/mvp_small.json
```

## 随机键

每个随机结果由以下字段决定：

```text
run_seed, tick, simulation_phase, subject_id, stream_id, draw_index
```

因此主体数组顺序变化或增加无关日志不会改变既有主体的随机序列。

## 当前社会主体实现

社会群体不是预先指定的奖励对象。高信任关系形成局部连通结构后，系统将其识别为候选群体，并计算群体的平均资源方向。该方向通过群体控制通道参与成员行动，但成员是否接受由其遗传社会倾向和行动采样决定。

## 社会方向引导（可配置建模规则）

`control.heuristic_social_guidance` 默认是 `false`，以保持既有基线实验可复现；启用后，候选社会主体会以其稳定的主体 ID 提交一份与身体策略对齐的方向提案。`HeuristicSocialGuidanceArbiter` 是当前已实现的社会控制规则：它只对已由身体策略采样为 `MOVE_RESOURCE` 的行动，将身体方向和已发布的群体资源方向按 `heuristic_social_guidance_weight`（0 到 1）混合并归一化。它不会改变动作类别、动作 mask 或随机键。

方向混合是明确记录的建模启发式，而不是主体性评分、因果归因或社会决策理论的证明。`run_metadata.json` 会记录配置、仲裁器名称和实际受引导行动数；若启用轨迹记录，`trajectory.jsonl` 还会写入 `heuristic_control`、全部贡献主体 ID 和贡献权重。关闭该选项时，默认单身体提案路径、随机流和 GPU 数据边界保持不变。

例如，在实验配置中显式启用：

```json
"control": {
  "heuristic_social_guidance": true,
  "heuristic_social_guidance_weight": 0.25
}
```

## 架构入口

- `random_api.py`：统一采样；
- `backend.py`：可选 NumPy/CuPy 后端与显式主机/设备转换；
- `gpu_environment.py`：设备版环境与信息场阶段；
- `gpu_runtime.py`：GPU 观察/策略与 CPU 世界提交之间的显式边界；
- `spatial.py`：空间索引与局部伙伴采样；
- `information.py`：传播和接收误差；
- `policy.py`：可替换策略接口的首个参数化实现；
- `control.py`：控制提案、仲裁协议、完整贡献来源审计和可选启发式社会引导；
- `execution.py`：可插拔冲突解析器和不可变行动解析计划；
- `social.py`：关系和候选群体；
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
