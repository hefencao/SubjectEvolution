# Subject Evolution 项目状态

版本：**0.25.0**

## 本轮输入

用户提供的 `natural-event-paired-intervention-matrix-v1` 通过计划哈希检查，包含 18 个锚点：3 seeds × scarcity/crowding/mortality × 每类 2 个。选择协议只读取 exposure、区域 alive、tick 和 checkpoint 可用性，事后凝聚度、传播、文化根、谱系和动作结果均被排除。

全部锚点有六个可执行消融；danger evidence 因旗舰配置为 disabled 而正确标记不可识别。scarcity 锚点的 z-score 约 0.55–0.60，明显低于 crowding/mortality 的 3.3–3.9，说明 scarcity exposure 接近饱和；不同 event kind 不应按 z-score 直接排名。

## v0.25 新增能力

### 已签名 manifest 执行层

`subject_evolution.natural_event_execution`：

- manifest 与执行计划分离，执行阶段不重新选择锚点；
- `--path-prefix OLD=NEW` 支持绝对路径迁移；
- checkpoint、progress、resolved config SHA-256 预检；
- seed、event、anchor 和 intervention 过滤；
- 相同 checkpoint/intervention 共享轨迹；
- 完成 marker 与安全续跑；
- anchor-level 和 seed-level paired delta 汇总。

用户 manifest 的直接规模为 126 branches；16 个唯一 checkpoint 经去重后为 112 trajectories，减少 14 条（11.1%）。

### 发行布局

- 根目录只保留 `README.md`、`pyproject.toml` 和运行脚本；
- 稳定文档位于 `docs/`；
- 版本实现与报告位于 `docs/v0.24/`、`docs/v0.25/`；
- 新压缩包不包含 `docs/archive`；完整历史仍可从旧版本发行包获得。

## 当前实现矩阵

| 领域 | 状态 | 边界 |
|---|---|---|
| CPU reference | 完成 | 当前科学语义权威 |
| GPU strict-reference | 完成 | 验证设备，执行 reference 世界 |
| GPU hybrid-accelerated | 部分完成 | 长程 parity 未证明 |
| 四资源异步生态位 | 完成 | 任意信息通道 schema 未完成 |
| 环境插件 ABI | 完成 | 非负标量场、默认关闭、无实体访问 |
| 实体/生命周期/谱系 | 完成 | 主要提交仍在 CPU |
| 遗传策略 | 完成 | 固定 8 actions × 16 features |
| 社会关系与 adaptive groups | 完成 | 候选主体结构；可 freeze 消融 |
| K1–K4 动态知识 | 完成 | 内容、承载副本、主体分离 |
| 有代价传播与局部文化诊断 | 完成 | 传播存在不等于适应性 |
| L1/L2、路由成本、工作记忆、Top-k | 完成 | 均可 checkpoint 与消融 |
| 资源亲和、mortality trace | 完成 | 适应价值仍需 paired branches |
| natural-event manifest planner | v0.24 完成 | 暴露盲选、哈希预注册 |
| manifest execution runtime | **v0.25 完成** | 路径映射、预检、去重、续跑、seed 汇总 |
| 任意嵌套主体数据库 | 未完成 | 当前是候选图与摘要 |
| 主体性/主体偏移评分 | 未完成 | 不允许由单一代理推出 |
| Hero RL、多 GPU | 未完成 | 当前非科学优先级 |

## 验证

- 全量测试：`123 passed, 1 skipped`；
- v0.24→v0.25 默认 CPU 20 tick：1606 个共同非计时 metrics 单元零差异；
- `evolution_progress.jsonl` byte-identical；
- v0.24 tick-10 checkpoint 由 v0.25 恢复到 tick 20，simulation state 与连续 v0.25 完全一致；
- 用户 manifest：18 anchors、126 naive branches、112 trajectories；
- 不含显式 `wheel` 的 pyproject 在当前环境成功构建 `subject_evolution_mvp-0.25.0` wheel。

## 下一阶段

1. 用户在原项目路径或使用 `--path-prefix` 后运行 v0.25 preflight；
2. 优先按 event kind 分批执行，避免 scarcity 与其他 exposure 的尺度混合；
3. 每批先完成 baseline + 单一 intervention，确认 marker/resume 与磁盘容量；
4. 分析时以 seed-level 方向为主，anchor-level 只作局部异质性展示；
5. 先运行 `disable-knowledge-transfer`、`freeze-group-refresh`、`neutralize-resource-affinity` 三个主机制，再扩展到知识策略、memory、Top-k；
6. danger evidence 保持 ineligible，除非使用预注册启用该 schema 的独立配置；
7. 真实 CUDA hybrid parity 继续独立推进，不与机制结论混合。

继续不采用：按谱系/群组奖励、自动保护多样性、提高跨组惩罚、单纯提高 mutation rate、环境层第二套生物实体，以及将观察性群组指标直接命名为主体性。
