# 长期分析 v5

## Schema

```text
multi-seed-long-run-analysis-v5
```

v5 兼容 v1–v4 的进度文件，并在存在 v0.20 字段时增加局部文化传播 panel。

## 新增输出

### 执行后端上下文

分析器从 `run_manifest.json` 和 `resolved_config.json` 读取：

- requested backend；
- execution backend；
- GPU semantics mode；
- CUDA device 是否经过验证；
- 是否启用实验性加速路径。

这用于区分 `gpu-strict-reference` 与 `hybrid-accelerated`。前者要求可用 GPU，但权威世界轨迹仍遵循 CPU reference 语义。

### 局部文化 panel

在 `window × region` 面板中分析局部压力、凝聚和文化传播，提供：

- 原始相关；
- 区域内去均值相关；
- 窗口内去均值相关；
- 一阶差分；
- 下一窗口关系。

### 观察性事件研究

分析器可以从局部稀缺、拥挤和死亡峰值构造描述性事件窗口，比较事件前后：

- 凝聚度；
- incoming/outgoing transfer；
- 新文化根和净建立；
- 活跃文化根；
- 同区域传播留存。

若没有足够的有效凝聚窗口或局部实体数量，事件数会是 0，而不会降低阈值强行制造事件。

### 跨 seed 方向一致性

全局指标和局部指标分别汇总符号一致性。重复符号支持稳健性，不表示必要性或因果性。

## 使用

```bash
python -m subject_evolution.long_run_analysis \
  runs/seed_10001/evolution_progress.jsonl \
  runs/seed_10002/evolution_progress.jsonl \
  runs/seed_10003/evolution_progress.jsonl \
  --output analysis/local_culture
```
