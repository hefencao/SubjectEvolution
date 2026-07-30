# 三 seed 长跑方向评估

## 数据范围

配置：

```text
mvp_short_latent_l2_memory_topk_inherited_heterogeneous_budget_matched_costed_transfer_mortality_trace_adaptive_groups_longrun.json
```

seed 10001、10002、10003 均运行至 tick 1500，每个 run 有 50 个长期窗口。环境过程和 danger evidence 均关闭；mortality trace 与 adaptive group refresh 开启。

## 终点

| Seed | Alive | 有效遗传世系 | 最大世系 | 策略维度 | 动作熵 | 凝聚度 | 传播提交 | 有效 transferred roots |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 10001 | 1360 | 15.777 | 16.18% | 14.007 | 1.736 | 0.265 | 12,166 | 2,011.22 |
| 10002 | 1352 | 21.073 | 11.54% | 19.426 | 1.747 | 0.371 | 12,460 | 2,051.12 |
| 10003 | 1328 | 21.303 | 13.18% | 18.802 | 1.735 | 0.336 | 14,168 | 2,183.63 |

传播已经跨主体、跨谱系和跨群组发生，文化传播指标可解释为“发生了内容传播和持续承载”；这些数字本身不证明传播具有适应性收益。

## 跨 seed 稳定局部方向

- scarcity 与新 transferred roots：正方向；
- scarcity 与净 transferred-root establishment：负方向；
- crowding 与 outgoing transfer rate：正方向；
- crowding 与下一窗口 cohesion：负方向；
- mortality 与 incoming transfer rate：弱正方向；
- scarcity 与下一窗口 cohesion：正方向；
- mortality 与下一窗口 cohesion：弱正方向。

这组模式提示不同压力轴的作用并不等价：稀缺可能增加知识根周转，却降低净建立；拥挤可能促进传播活动，同时削弱群组内部留存。不能再把它们合并成单一“生存压力”。

## 全局指标的限制

mortality 与 cohesion 的 raw/partial 方向在三个 seed 中为正，但 mortality 与下一窗口 cohesion 的首差分近于零且为负。有效世系与 cohesion 的 raw、difference、partial 均为负，但最大世系占比的 partial 方向不一致。这说明共享时间趋势和人口相位仍然重要。

## v0.24 方向

1. 不增加新的生态规则或生物型危险源；
2. 用 scarcity、crowding、mortality 三类自然事件分别选择锚点；
3. 锚点选择不读取事后 cohesion、文化根或谱系结果；
4. 在同一 checkpoint 执行 transfer、knowledge-policy、working-memory、Top-k、resource-affinity 和 group-refresh 消融；
5. 当前 danger evidence disabled，必须标记不可识别；
6. 只有 paired matrix 表明现有证据轴不足，才考虑新增非生物环境过程。

## 解释边界

本分析是观察性的。跨 seed 同号支持重复方向，不证明机制必要性；自然事件配对分支也只识别给定事件和 horizon 下的机制关闭效应，不把自然事件转化为随机试验。
