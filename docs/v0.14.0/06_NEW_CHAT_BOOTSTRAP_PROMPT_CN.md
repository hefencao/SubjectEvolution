# 新聊天窗口启动提示词

下面的内容可直接复制到新的聊天窗口。建议同时上传：

- `subject_evolution_v014_project.zip`
- 本交接文档包 `subject_evolution_v014_handoff_docs.zip`
- 若要分析实验，再上传 `subject_evolution_v014_results.zip` 或具体 `parity_report.json`

---

我在继续开发一个 Python 演化模拟项目 `Subject Evolution`。当前权威版本是 **v0.14.0**，源码包为 `subject_evolution_v014_project.zip`。请先完整阅读源码包中的：

1. `PROJECT_STATUS.md`
2. `EVOLVABLE_SELECTION_IMPLEMENTATION.md`
3. `CAUSAL_ABLATION_IMPLEMENTATION.md`
4. `CPU_GPU_PARITY.md`
5. `WORKING_MEMORY_IMPLEMENTATION.md`
6. `SPARSE_KNOWLEDGE_SELECTION_IMPLEMENTATION.md`
7. `LATENT_ROUTING_COST_IMPLEMENTATION.md`
8. `LATENT_ROUTER_MLP_IMPLEMENTATION.md`
9. `LATENT_KNOWLEDGE_IMPLEMENTATION.md`
10. `K1_IMPLEMENTATION.md` 到 `K4_IMPLEMENTATION.md`
11. `CHECKPOINT_REPLAY_IMPLEMENTATION.md`
12. `FINAL_TEST_REPORT.txt`

项目当前已实现：

- K1 动态知识内容/副本、容量、成本、交换、损坏和遗忘；
- K2 本地 context/action 的五维后果学习；
- K3 稀疏知识 action-logit residual；
- K4 内容谱系和候选主体图诊断；
- 完整 `.sechk` checkpoint 恢复与离线共同历史反事实；
- 4/8/16/32 维可变长度潜知识；
- L1 量化线性路由和 L2 量化两层 MLP；
- 路由计算成本与 all-or-none 实体能量预算；
- 四维量化工作记忆；
- 无全局类别 embedding、无 Softmax 的 stable Query-Key Top-k 临时工作集；
- 实体级遗传离散 Top-k 容量 `0/1/2/4/8`；
- `ablate-working-memory` 和 `bypass-sparse-selection` checkpoint 干预。

必须保持的科学和工程边界：

- 不引入外部集中训练、global reward、backprop 或未来信息；
- 知识可以使用潜空间和小型路由器，但所有影响必须经过公开 policy residual、成本审核、intent、resolution 和 commit；
- 五维后果不压缩为单一 reward；
- 完整知识权威状态是动态 SoA，Top-k 只是 ephemeral 工作集，不能退化成固定 `K_max` 权威容量；
- 不使用设计者预设的全局类别 embedding 作为控制语义；
- 普通 float Softmax Attention 暂不进入正式路径；
- 新机制必须独立 schema，默认关闭时保持旧配置兼容；
- 新机制必须有成本、贡献日志、checkpoint/replay、单测和短周期对照；
- CPU/GPU 离散动作和稳定 ID 要求逐位一致，不能只接受“小浮点误差”；
- 用户偏好单元测试 + 20-50 ticks 短验证，不要默认反复跑 500 ticks；
- 不要夸大单 seed、短周期结果，不要声称主体性或长期适应优势；
- 当前开发环境没有 CUDA，必须如实说明真实 GPU 未验证范围。

CPU/GPU 历史：K2 hybrid 路径已由用户在真实 GPU 上运行至 tick 1000，无偏差；v0.14 的 latent L2、工作记忆、Top-k、遗传容量和成本尚未完成真实 CUDA world parity。正式 GPU 默认是 `strict-reference`，`hybrid-accelerated` 为实验路径。

历史重要 bug，避免重复：

- parity 工具曾凭空假设 `relation_target` 属性；必须读真实类结构；
- NumPy/CuPy FP32 `reduceat` 归约顺序导致信息/资源持久场分歧；
- float32 周期取模可能返回精确上界；
- hybrid GPU 曾漏传 knowledge policy plan；
- 潜长度变体必须在容量/传输审核前预演目标字节；
- 实体级 selection 工作量不能按 nonzero action 重复累计。

当前测试状态：64 tests，63 passed，1 个真实 CUDA 测试 skip。固定 K 的 v0.13/v0.14 共同状态兼容；遗传容量双重复确定。

建议下一步优先级：

1. 在真实 GPU 上运行 `subject_evolution.parity`，验证 v0.14 requested capacity、selected IDs/scores、working memory、L2 residual、成本、action 和完整 world checkpoint；
2. 若失败，只根据首个差异修复，不根据最终 alive 猜测；
3. 若通过，建立多 seed、多 intervention tick 的 memory/selection 因果矩阵；
4. 再考虑单内容/单谱系消融或局部可塑性。

请直接执行任务，不要重复询问已经在文件或本提示中提供的信息。对复杂任务给简短进度更新；如无法完成某硬件验证，要明确说出限制并交付可在目标主机运行的诊断工具。

---
