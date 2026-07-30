# Subject Evolution v0.14.0 交接资料入口

这套文档用于在新的聊天窗口、开发环境或协作者之间继续推进 `Subject Evolution` 项目。

## 建议阅读顺序

1. `01_PROJECT_OVERVIEW_CN.md`：了解项目目标、整体架构与科学原则。
2. `02_PROJECT_PROGRESS_CN.md`：了解从初始拆分到 v0.14.0 的演进。
3. `03_ARCHITECTURE_AND_SCIENCE_BOUNDARIES_CN.md`：了解不能破坏的设计边界。
4. `05_HANDOFF_REPORT_CN.md`：接手前必须知道的当前状态、风险和下一步。
5. `04_RUNBOOK_CN.md`：运行、测试、parity、checkpoint 和重放命令。
6. `06_NEW_CHAT_BOOTSTRAP_PROMPT_CN.md`：复制到新聊天窗口作为启动提示词。
7. `07_ARTIFACT_INDEX_CN.md`：项目包、结果包和关键源码/报告索引。
8. `08_VERSION_AND_SCHEMA_MATRIX_CN.md`：版本、schema、基因组与兼容性矩阵。

## 当前权威版本

- 项目版本：`0.14.0`
- 源码包：`subject_evolution_v014_project.zip`
- 结果包：`subject_evolution_v014_results.zip`
- Python：`>=3.10`
- 必需依赖：`numpy>=1.24`
- GPU：需要与本机 CUDA 匹配的 CuPy；当前交付环境没有可用 CUDA，因此 v0.14.0 真实 GPU world parity 尚未完成。

## 当前最重要的事实

- K1-K4、完整 checkpoint/replay、可变长度潜知识 L1/L2、计算成本、工作记忆、稀疏 Top-k 和实体级遗传 Top-k 已实现。
- K2 hybrid GPU 路径曾由用户在真实 GPU 上运行至 tick 1000，未发现 CPU/GPU 偏差。
- v0.10-v0.14 新增的潜路由、工作记忆、选择器、成本和遗传容量只完成 CPU reference、模拟设备和短周期确定性验证；真实 CUDA 多 tick world parity 仍需完成。
- 固定知识槽、全局类别 Embedding 和普通 float Softmax Attention 没有进入权威路径，以避免容量退化、人工预设和 parity 风险。
- 默认测试偏好是单元测试加 20-50 ticks 短验证；除非问题只在长轨迹出现，不要默认反复运行 500 ticks。
