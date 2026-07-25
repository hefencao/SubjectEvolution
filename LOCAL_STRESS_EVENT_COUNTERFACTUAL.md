# 局部压力事件 checkpoint 反事实（v0.20.0）

## 目的

全局人口峰谷不再是空间异步环境中的可靠干预时点。该执行器从单个区域的稀缺、死亡或拥挤峰值选择事件，并映射到事件之前最近的可信 `.sechk`。

## 事件选择

```text
scarcity / mortality / crowding
```

事件必须满足：

- 同一区域至少 5 个有效窗口；
- 区域凝聚度有效；
- 区域至少 5 个存活实体；
- 超过该区域配置分位数；
- 是局部时间峰值；
- 存在严格早于事件的 checkpoint。

选择仍是观察性的，不能把事件前后变化解释为环境压力的因果效应。

## 配对干预

默认分支：

- `disable-knowledge-transfer`；
- `disable-knowledge-policy`；
- `ablate-working-memory`；
- `bypass-sparse-selection`。

所有分支从同一 checkpoint、同一 keyed randomness 开始。输出目标区域的：

- alive；
- cohesion；
- incoming/outgoing commits；
- active/new/lost transferred roots。

若 checkpoint 前尚未发生成功传播，transfer-off 会标为不可识别。

## CLI

```bash
python -m subject_evolution.local_event_counterfactual \
  --run-dir runs/local_stress_multiseed/seed_10001 \
  --output runs/local_event_counterfactual_seed10001 \
  --event-kind scarcity \
  --event-quantile 0.85 \
  --max-events 4 \
  --horizon 120 \
  --backend cpu
```

## 管线样例边界

20-tick 手工验证事件中，停止未来传播令目标区 incoming/outgoing commits 和活跃文化根各减少 1；关闭知识 residual 令目标区 alive 增加 1、凝聚度变化约 0.0633。该结果仅验证分支工具链，不构成长期机制证据。
