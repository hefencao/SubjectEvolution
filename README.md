# 嵌套主体存在演化模拟：v0.3 GPU 基础阶段

这是项目规范的可运行 CPU 参考内核和分阶段 GPU 基础实现。v0.3 已迁移随机键、环境/信息场及规则网格，但完整 GPU 世界循环仍会在后续阶段逐项接入，避免破坏 v0.2 固定的行动语义。

## 已实现

- 圆球物理承载体与身体、谱系、社会候选主体的概念分离；
- 固定容量SoA实体状态；
- 二维周期世界与四类不可完全替代资源；
- 季节变化、危险场和三通道信息场；
- 相邻网格局部伙伴采样，无全体两两搜索；
- 无状态随机键及统一Bernoulli、Normal、Categorical采样；
- 可选 CuPy 后端：GPU 数组上的无状态随机键和基础分布；
- 设备版四资源环境、危险场、三通道信息场、规则网格和伙伴采样；
- 场发射与资源提交使用稳定排序、分段归约，不依赖浮点原子累加；
- 传播丢失、接收噪声、语义误分类和伙伴感知误差；
- 参数化共享策略、个体遗传潜变量和有限记忆；
- 行动采样、移动、采集、分享、发信号、繁殖和逃离；
- 行动提案、稳定意图ID、资源/分享/出生冲突的统一结算和执行记录；
- 区域信号场与固定容量、带延迟的点对点消息队列；
- 固定容量信任关系；
- 基于高信任关系的社会群体候选识别；
- 群体资源方向形成对成员行动的高层影响；
- 谱系继承、变异、出生、死亡和容量管理；
- 社会依赖代理指标、群体指标、信息检测率和行动熵；
- 身体、谱系和社会候选主体图，以及主体ID和实体ID的显式分离；
- 成对随机的反事实分支：关闭社会控制、切断社会连接、打乱记忆或冻结遗传；
- 检查点、CSV指标、运行元数据和基础测试。

## 尚未实现

- 完整 GPU 世界循环（观察、策略、行动、关系、出生死亡和主体图）；
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
export LD_LIBRARY_PATH="$CUDA_PATH/targets/x86_64-linux/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
python -m pytest -q
```

若系统的 CUDA 安装目录不同，请把 `CUDA_PATH` 改为实际路径。上述变量让 CuPy 在 WSL 中定位工具包和动态库；可将它们写入 Conda 环境激活脚本以免每次重复设置。

开发测试：

```bash
pip install -e '.[dev]'
pytest
```

## 运行小型演示

```bash
python -m subject_evolution.cli \
  --config configs/mvp_small.json \
  --output runs/demo
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

- `metrics.csv`：周期指标；
- `summary.json`：最后一条指标；
- `run_metadata.json`：运行时间和累计动作；
- `checkpoint_*.npz`：抽样检查点；
- `config.json`：实际运行配置副本。

## 运行10万实体配置

```bash
python -m subject_evolution.cli \
  --config configs/mvp_100k.json \
  --output runs/mvp_100k
```

当前版本是CPU参考实现，10万实体配置用于验证数据和机制，不保证实时速度。完成CPU回归测试后，GPU版本应保持相同配置、随机键、观察schema和行动语义。

在有 CUDA 的机器上，先对已迁移阶段运行对照：

```bash
conda activate se
export CUDA_PATH=/usr/local/cuda-13.3
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

## 架构入口

- `random_api.py`：统一采样；
- `backend.py`：可选 NumPy/CuPy 后端与显式主机/设备转换；
- `gpu_environment.py`：设备版环境与信息场阶段；
- `spatial.py`：空间索引与局部伙伴采样；
- `information.py`：传播和接收误差；
- `policy.py`：可替换策略接口的首个参数化实现；
- `social.py`：关系和候选群体；
- `simulation.py`：阶段化世界执行；
- `environment.py`：资源、气候和危险。

## 批量实验

```bash
python scripts/run_sweep.py --output runs/sweep --ticks 200 --seeds 3
```

该脚本比较低噪声/低温、基线和高噪声/高温条件，并输出`sweep_summary.csv`。

## 设计文档

- `docs/IMPLEMENTATION_STATUS.md`：v0.3完成度与已知简化；
- `docs/GPU_FOUNDATION.md`：GPU 基础阶段、对照语义与运行要求；
- `docs/NEXT_GPU_PHASE.md`：GPU迁移顺序；
- `docs/specification/`：项目总规范和四份工程规范。
