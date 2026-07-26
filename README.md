# Subject Evolution v0.31

一个以**可审计世界状态、局部交互、遗传策略、动态知识、生态分化和候选主体结构**为核心的演化模拟参考实现。

v0.31 开始落实更新后的 [项目立项文档 v0.3](docs/PROJECT_CHARTER_V0.3.md)：先建立真正可分化的环境与生态位，再逐步推进弹性容量、功能模块、生态关系、社会结构和高层主体。

## v0.31：D0 环境正交化

新增科学核心环境 schema：

```text
orthogonal-four-resource-niche-v1
```

它继续使用既有四个物理资源通道，但允许每个通道拥有独立的：

- 空间主/次波向量；
- 时间周期、相位和振幅；
- 扩散速率；
- 对能量、完整性、信息材料、繁殖材料等生命用途的作用矩阵。

环境场不读取实体、谱系、群组或策略，不追逐种群，也不自动保护多样性。它只提供版本化的外生选择轴；是否产生生态型、功能分化和长期共存仍必须由演化实验检验。

## D0 主线配置

```bash
python -m subject_evolution.multi_seed \
  --config configs/mvp_short_d0_orthogonal_environment_longrun.json \
  --seeds 10001,10002,10003 \
  --output runs/d0_orthogonal_environment_multiseed \
  --backend gpu \
  --until-tick 1500
```

请求 GPU 时仍建议使用配置中的 `gpu_semantics_mode="strict-reference"`：设备被验证，但科学世界由 CPU reference 语义权威执行。

短程集成配置：

```bash
python -m subject_evolution.cli \
  --config configs/d0_orthogonal_environment_smoke.json \
  --output runs/d0_smoke \
  --backend cpu
```

## 无实体环境维度审计

```bash
python -m subject_evolution.environment_diversity \
  --config configs/mvp_short_d0_orthogonal_environment_longrun.json \
  --output analyses/resource_diversity \
  --ticks 600 \
  --sample-period 10
```

该审计在不进行实体采集的情况下报告：

- 四资源空间有效维度；
- 通道相关矩阵及平均/最大绝对相关；
- 时间变化有效维度；
- 每个采样 tick 的维度保持情况。

当前预注册配置的 600-tick 外生审计得到：空间有效维度均值 `3.8670`、最低 `3.6497`；这证明配置提供了多条独立环境轴，但不证明生物分化已经发生。

## Multiscale atlas v2

```text
multiscale-subject-environment-atlas-v2
```

atlas 除原有综合 signature 外，新增资源自身的：

- effective dimensions；
- channel correlation matrix；
- mean/max absolute correlation。

这避免 hazard 或 mortality trace 掩盖资源通道是否真正独立。

## 协议与长程分析

```bash
python -m subject_evolution.protocol_audit \
  --config configs/mvp_short_d0_orthogonal_environment_longrun.json \
  --output analyses/protocol_audit
```

protocol audit v3 发布资源周期、波向量、扩散、作用矩阵和非实体感知边界。long-run analysis 升级为 v10；structure–environment analysis 升级为 v2。

## 科学边界

- 四资源通道及其物理作用接口仍由模型版本定义；v0.31 实现的是**固定接口内的独立环境轴**，不是无限环境 vocabulary。
- 高环境维度不等于生态位形成；必须检查遗传性状、容量、资源使用和相对适应优势是否发生条件性分化。
- 当前 D0 不实现通用功能模块、基因复制或动态容量；这些属于 D1–D3。
- 不引入第二套具有出生、死亡、策略或谱系的危险实体。
- 主体 succession 与环境 association 仍是诊断，不是主体身份或环境因果定理。

## 文档

- [项目立项文档 v0.3](docs/PROJECT_CHARTER_V0.3.md)
- [分化架构评估](docs/DIFFERENTIATION_ARCHITECTURE_ASSESSMENT.md)
- [当前项目状态](docs/PROJECT_STATUS.md)
- [科学问题与研究债务](docs/SCIENTIFIC_ISSUES.md)
- [架构与提交边界](docs/ARCHITECTURE.md)
- [v0.31 文档](docs/v0.31/README.md)

发行压缩包不包含 `docs/archive`。历史材料保留在此前版本发行包中。
