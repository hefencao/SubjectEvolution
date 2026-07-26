# v0.32 Python 性能与迁移评估

## 基准范围

共同命令：

```bash
python -m subject_evolution.cli \
  --config configs/d0_orthogonal_environment_smoke.json \
  --backend cpu \
  --until-tick 120
```

该配置启用高容量 knowledge 审计日志，最终 alive=163。结果只用于定位当前实现热点，不能外推到所有实体规模或真实 CUDA。

## 结果

### 无 profiler wall time

| 版本 | 三次 wall time | 均值 | 中位数 |
|---|---|---:|---:|
| v0.31 | 8.35 / 9.02 / 9.33 s | 8.90 s | 9.02 s |
| v0.32 | 7.10 / 7.28 / 7.09 s | 7.16 s | 7.10 s |

中位数下降约 21.3%，均值下降约 19.6%。主要来自缓存 CuPy 可用性检测；v0.31 在低层数组工具中反复执行可选 import discovery。

### cProfile

| 指标 | v0.31 | v0.32 |
|---|---:|---:|
| 总 profile 时间 | 17.597 s | 11.794 s |
| function calls | 28,988,445 | 20,351,280 |
| `Simulation.step` cumulative | 16.755 s | 11.254 s |

当前主要热点：

| 热点 | cumulative | 解释 |
|---|---:|---|
| `KnowledgeLoggingMixin.record_policy_plan` | 4.166 s | 每个非零 action residual 生成大字典并写 CSV |
| CSV `writerow` | 3.063 s | 120 ticks 产生约 18.2 万行；贡献日志约 25 MB |
| `KnowledgeSystem.commit_outcomes` | 1.895 s | holder/content 局部结果更新与索引操作 |
| latent policy plan | 1.437 s | 稀疏选择、哈希投影、路由和量化 |
| latent signed hash / catalog projection | 约 2 s 合计 | 大量 Python/NumPy 小操作与重复哈希 |

环境场、空间索引和基础 policy 不是该小规模 CPU 基准中的主要耗时。

## 判断

### 已存在 Python 性能瓶颈

是。当前瓶颈主要位于：

1. **逐事件 Python 对象/字典构造与 CSV 写入**；
2. **knowledge outcome/latent routing 中的大量细粒度循环和小数组操作**；
3. GPU 路径仍非完整设备驻留，strict-reference 科学运行由 CPU reference 权威执行。

但这不支持立即整体重写。当前最昂贵的一项是可关闭的审计 I/O，而不是世界物理计算；先迁移语言会把日志和协议复杂度搬到更难验证的实现中。

## 推荐迁移路线

### P0：继续保留 Python 作为编排和科学协议层

Python 继续负责：

- 配置/schema 和预注册验证；
- 实验计划、checkpoint lineage 和结果综合；
- 离线分析和文档生成；
- reference implementation 与 parity oracle。

### P1：先处理日志和数据布局

优先级高于语言迁移：

- 将逐行贡献日志改为可配置 sampling/aggregation；
- 在保持字段与顺序的条件下批量编码；
- 为长跑增加 columnar/分块 writer，但保留 CSV 兼容导出；
- 禁止在不需要因果审计时默认产生每 action-cell 日志；
- 把高容量日志耗时单独计入 metrics。

### P2：以 CuPy custom kernels 推进设备驻留热点

适合迁移：

- latent hash/projection；
- Top-k score、tie audit 与量化路由；
- outcome 聚合和 holder segmented reductions；
- birth/death plan 的固定布局预处理。

应通过固定整数/定点路径、固定归约顺序和 CPU reference parity 保持科学语义。

### P3：只为已证明热点引入 C++/CUDA 扩展

当一个 phase 同时满足以下条件时再迁移：

- 占目标长跑时间至少约 20%；
- 数据边界稳定并有版本化 plan/result；
- 有 CPU reference 和逐阶段 parity；
- Python 优化、批处理和 CuPy kernel 仍不足；
- 可在无 GPU 环境保持 reference fallback。

推荐 Python 胶水 + C++/CUDA kernel library，而非把整个项目重写为 C++。若未来 CPU 服务器是主目标，可对相同 plan API 实现 C++ 或 Rust CPU backend，但不能同时维护两套不同世界规则。

## Compute shader 评估

Compute shader 适合：

- GUI 预览、热图、粒子可视化；
- 非权威的交互式近似模拟；
- 与 renderer 同进程的观察工具。

不建议把当前科学权威世界迁到通用 graphics/WebGPU compute shader：

- WGSL/WebGPU 允许实现间浮点精度差异、flush-to-zero 和不同实现方式；
- 当前项目要求 fixed rounding、stable aggregation、trusted checkpoint 和 CPU/GPU parity；
- 图形 API 的驱动、vendor 和 shader compiler 差异会扩大验证矩阵；
- Python/CuPy/CUDA 已有更直接的数组和 device-memory 边界。

若使用 compute shader，应明确标记为 `preview/non-authoritative`，不得生成科学 checkpoint 或与 reference results 混合。

## 决策

当前结论：

```text
不整体迁移语言。
保留 Python reference/orchestration。
先降低审计 I/O，再将已证明的数值热点迁入 CuPy RawKernel/C++ CUDA。
Compute shader 仅用于可视化或非权威预览。
```
