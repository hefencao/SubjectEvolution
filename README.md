# 嵌套主体存在演化模拟：第一版参考实现

这是项目规范的首个可运行实现。它优先完成CPU参考内核、因果分阶段执行和统一采样，而不是直接追求最终GPU规模。

## 已实现

- 圆球物理承载体与身体、谱系、社会候选主体的概念分离；
- 固定容量SoA实体状态；
- 二维周期世界与四类不可完全替代资源；
- 季节变化、危险场和三通道信息场；
- 相邻网格局部伙伴采样，无全体两两搜索；
- 无状态随机键及统一Bernoulli、Normal、Categorical采样；
- 传播丢失、接收噪声、语义误分类和伙伴感知误差；
- 参数化共享策略、个体遗传潜变量和有限记忆；
- 行动采样、移动、采集、分享、发信号、繁殖和逃离；
- 资源竞争统一结算；
- 固定容量信任关系；
- 基于高信任关系的社会群体候选识别；
- 群体资源方向形成对成员行动的高层影响；
- 谱系继承、变异、出生、死亡和容量管理；
- 社会依赖代理指标、群体指标、信息检测率和行动熵；
- 检查点、CSV指标、运行元数据和基础测试。

## 尚未实现

- CUDA内核和真正GPU执行；
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

- `docs/IMPLEMENTATION_STATUS.md`：本版本完成度与已知简化；
- `docs/NEXT_GPU_PHASE.md`：GPU迁移顺序；
- `docs/specification/`：项目总规范和四份工程规范。
