# v0.3 GPU 基础阶段

本阶段只迁移 `NEXT_GPU_PHASE.md` 中最前置、可独立对照的三个阶段：无状态随机键、环境/信息场，以及规则网格与伙伴采样。完整模拟仍默认使用 CPU 参考内核；在行动、关系、出生死亡和主体图都迁移前，禁止混合执行半条 GPU 世界路径。

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
export LD_LIBRARY_PATH="$CUDA_PATH/targets/x86_64-linux/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
```

若 CUDA 安装位置不同，改用该位置；建议将变量放入 `se` 环境的激活脚本。CPU 模式不依赖这些变量。

## 已迁移语义

| 阶段 | GPU组件 | 对照规则 |
|---|---|---|
| 1 | 无状态键、Uniform、Bernoulli、Normal、Categorical | 相同随机键应给出相同离散结果；浮点分布按容差比较 |
| 2 | 四资源场、危险场、三通道信息场 | 固定配置和 tick 下比较字段、年龄及采集分配 |
| 3 | cell ID、稳定排序、cell 边界、局部伙伴采样 | 稳定 ID 不变；固定种子下伙伴槽位一致 |

所有高竞争字段写入采用稳定 `(cell_id, 原始顺序)` 排序和分段归约。每个 cell 最后只写一次，避免 GPU 浮点 `atomicAdd` 的非确定累加顺序。

GPU数组仅包含原本的世界字段。策略仍只读取既有观察结构，不能读取 cell 排序、中间归约或设备诊断数据。

## 验证方式

测试套件始终运行 NumPy 对照；检测到可用 CuPy 时还会运行 GPU 对照。建议在目标设备上执行：

```bash
conda activate se
export CUDA_PATH=/usr/local/cuda-13.3
export LD_LIBRARY_PATH="$CUDA_PATH/targets/x86_64-linux/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
python -m pytest -q
```

对环境、信息场和资源提交的独立性能/一致性检查：

```bash
python scripts/verify_gpu_foundation.py --config configs/mvp_small.json
```

本工作区已在 WSL2、NVIDIA GeForce RTX 4070、CUDA Toolkit 13.3 和 `cupy-cuda13x==14.1.1` 上验证：完整测试套件为 `25 passed`，`--ticks 16` 的字段最大绝对误差为 `2.12e-6`，小于 `5e-6` 容差。该小场景的计时只用于发现同步或回传问题，不能外推为完整世界循环的性能结论。

下一步将迁移观察构建和按策略批处理推理，再把这些已验证组件接入完整 GPU 世界循环。
