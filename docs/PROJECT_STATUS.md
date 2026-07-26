# Subject Evolution 项目状态

版本：**0.31.0**

## 当前主线

项目按照立项文档 v0.3 进入“环境与分化优先”阶段：

1. **D0 环境正交化**：建立不能由单一总体充足度解释的多条环境轴；
2. **D1 弹性容量**：分别演化记忆、知识、关系、传感、储存和模块容量；
3. **D2–D3 功能模块与结构突变**：固定物理接口内的表达、路由、复制、删除和新功能化；
4. **D4 生态位形成**：验证多个生态型的条件性优势和长期共存；
5. **D5 社会与高层主体**：在真实功能互补和生态依赖之后推进公共状态和控制。

v0.31 完成 D0 的首个世界机制版本。v0.30 的主体 succession 继续保留为观察性诊断，但不再是当前首要实现目标。

## v0.31 新增

### Orthogonal resource environment

- schema：`orthogonal-four-resource-niche-v1`；
- 四个已有资源通道分别配置空间主/次波、时间周期、相位、振幅和扩散率；
- `resource_effect_matrix` 明确不同资源的身体用途；
- 环境不读取实体、谱系、群组或策略，不保护多样性；
- 旧环境 schema 保留原路径。

### Resource diversity audit

- schema：`resource-environment-diversity-audit-v1`；
- 测量空间和时间资源有效维度；
- 发布通道相关矩阵及平均/最大绝对相关；
- 无实体采集审计不等于生态分化或选择实验。

### Atlas and analysis

- atlas：`multiscale-subject-environment-atlas-v2`；
- protocol audit：`structural-measurement-protocol-audit-v3`；
- long-run：`multi-seed-long-run-analysis-v10`；
- structure–environment：`multi-seed-subject-environment-analysis-v2`。

## 当前验证

- 600-tick 外生审计：空间资源有效维度均值 3.8670，最低 3.6497；
- 120-tick CPU smoke：最终全局资源有效维度 3.5183，4×4/8×8 atlas 为 3.9149/3.9209；
- 全量测试：150 passed，1 skipped；
- v0.30→v0.31 旧配置 20-tick：1974 个共同非计时 metrics 单元零差异；
- 8 类知识日志 byte-identical；
- v0.30 tick-10 checkpoint 可由 v0.31 精确续跑到 tick 20。

## 当前科学边界

1. 环境轴已经实现多维方差，但尚未证明遗传表型或生态型分化。
2. 固定四通道和身体作用端口仍是模型基底，不是“无限无预设功能”。
3. 资源通道方差高不保证每条轴都有相似选择强度；必须检查实际摄取、限制因子和繁殖结果。
4. 当前主体 succession 仍是 group-label 测量下的成员重叠，不是独立高层控制者。
5. D1/D2 尚未实现，不应把现有 latent router 或工作记忆重新命名为通用器官分化。

## 下一步实验

优先运行：

```text
configs/mvp_short_d0_orthogonal_environment_longrun.json
```

建议 3 seeds × 1500 ticks，随后检查：

- 资源有效维度随采集是否坍缩；
- 四资源实际限制强度和使用率；
- 资源亲和的跨区域、跨阶段条件性优势；
- 谱系和群组 association 是否超出空间聚集基线；
- 种群长期存续和生态型共存动态。

在获得这些结果前，不直接实施通用功能张量、模块复制或群体控制。
