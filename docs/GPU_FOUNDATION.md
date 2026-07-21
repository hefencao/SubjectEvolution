# v0.4 GPU 混合执行阶段

本阶段将已对照的 GPU 基础层接入运行时：无状态随机键、环境/信息场、规则网格、观察构建和参数化策略批处理。`--backend gpu` 是显式的混合模式：CPU 保留语义权威的世界提交，GPU 承担规模化数组计算。它不是“悄悄回退”的自动优化，也不是完整设备驻留世界循环。

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
| 4 | 场/伙伴观察、感知噪声、信息分类 | 观察 schema 不变；直接消息使用 CPU 批量解码后的固定张量 |
| 5 | 参数化策略、动作采样与方向选择 | 相同种子小场景动作一致；浮点状态按容差比较 |

所有高竞争字段写入采用稳定 `(cell_id, 原始顺序)` 排序和分段归约。每个 cell 最后只写一次，避免 GPU 浮点 `atomicAdd` 的非确定累加顺序。

GPU数组仅包含原本的世界字段。策略仍只读取既有观察结构，不能读取 cell 排序、中间归约或设备诊断数据。

## 混合边界

设备侧：环境与信息场更新、信号场发射、采集分配/提交、规则网格、伙伴采样、场与伙伴观察、策略 logits/采样/方向。

CPU侧：延迟消息队列的所有权及批量解码、行动意图和冲突记录、位置/能量提交、分享关系、出生死亡、群体识别、主体图、CSV 和检查点。直接消息以 NumPy 数组批次排队，分享关系按拥有者局部顺序分轮批处理；仅回传 CPU 提交实际需要的动作和观察摘要，资源梯度只在群体更新 tick 回传。稳定 ID、基因型和低频群体字段缓存在设备；批量 `run()` 在结束前才同步完整字段镜像。

行动冲突不属于某个设备后端：`execution.py` 接收只读 `ActionResolutionSnapshot` 和意图批次，输出不修改世界的 `ActionResolutionPlan`。默认解析器使用严格 CPU 排序；未来 GPU、分布式和回放解析器须实现同一协议，世界提交仍只接受计划中的 `ActionResolutionBatch`。

`step_seconds` 是世界 step 本身；`window_seconds_per_tick` 统计上一个报告窗口内的墙钟平均，包含日志和检查点等非 step 工作。应使用后者和 `run_metadata.json` 的 `wall_seconds` 判断实际吞吐。

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

本工作区已在 WSL2、NVIDIA GeForce RTX 4070、CUDA Toolkit 13.3 和 `cupy-cuda13x==14.1.1` 上验证：完整测试套件为 `35 passed`；三步 CPU/GPU 同种子场景动作计数一致，字段状态只存在小的 FP32 容差；`--ticks 16` 的字段最大绝对误差为 `2.12e-6`，小于 `5e-6` 容差。10万实体实际批量运行70步，首步 JIT 后第20/40/60步窗口平均为 `0.088/0.096/0.097秒`，仅作当前机器上的规模参考。

下一步将迁移动作冲突、关系事件、出生死亡和主体图，以减少主机边界并最终得到完整设备驻留循环。
