# CPU/GPU 语义一致性状态（v0.6.3）

## 结论

v0.6.1 的 `sensor_quality` dtype 修复不足以解决真实多 tick 世界分歧。用户在真实 GPU 上复现：

- `mvp_small_k2.json`：tick 100，CPU alive 8185，GPU alive 8186；
- `mvp_short_k2_exchange.json`：tick 160，CPU alive 1536，GPU alive 1535。

第二个配置包含知识交换，第一个复现点不依赖交换，因此知识交换不是必要条件。真正的
`hybrid-accelerated` 多 tick 根因仍需要真实 CUDA 上的首差异报告定位。

## v0.6.3 parity harness correction

The v0.6.2 world-parity diagnostic incorrectly referenced nonexistent
`SocialSystem.relation_target` / `relation_trust` attributes.  The actual
authoritative relation arrays are `target` and `trust`; `relation_targets` is
a field of `GroupDetectionSnapshot`, not of `SocialSystem`.

The diagnostic now builds a named snapshot from the array attributes actually
owned by `SocialSystem`.  The current compared arrays are `target`, `trust`,
`familiarity`, `last_interaction`, `last_decay_tick`, `group_id`, `group_age`,
`group_dir_x`, and `group_dir_y`.  Mapping comparisons preserve these names in
the parity report, and optional stage presence is compared explicitly rather
than silently skipped.

This fixes the diagnostic crash only.  It does not by itself establish that the
underlying hybrid CPU/GPU divergence has been fixed; a real CUDA run must now
use the corrected tool to identify the first semantic mismatch.


## v0.6.2 correctness gate

正式 `--backend gpu` 现在默认使用：

```text
gpu_semantics_mode = strict-reference
```

其行为是：

1. 显式 GPU 请求仍必须检测到可用 CuPy/CUDA；不可用时抛出 `BackendUnavailableError`，不会静默回退；
2. 世界更新、观察、策略、intent、冲突、出生死亡、知识和日志均以 CPU reference 路径为权威；
3. run manifest 明确记录 `execution_backend=gpu-strict-reference`、设备是否验证，以及 GPU acceleration 未启用；
4. 因为执行的是同一个 CPU reference 语义路径，正式 CPU/GPU 请求不会再形成不同的演化历史。

这是正确性优先的临时门禁，不是 GPU 性能修复。它会牺牲当前混合 GPU 加速，直到真实设备路径通过多 tick 离散字段一致性验证。

旧混合加速路径只能显式启用：

```bash
python -m subject_evolution.cli \
  --config configs/mvp_short_k2_exchange.json \
  --output runs/experimental_hybrid \
  --backend gpu \
  --gpu-semantics-mode hybrid-accelerated
```

`hybrid-accelerated` 会在 `scientific_validity` 中被标记为违规，不能作为正式 scientific baseline。

## 增强后的首差异定位

`subject_evolution.parity` 会强制使用实验混合路径，不受 strict-reference 默认值影响。现在逐 tick 比较顺序为：

1. active rows 与 cell IDs；
2. local resources；
3. policy 使用的 observation：signals、age、partner energy/group/mask、uncertainty；
4. policy features、logits、mask、action、probability、entropy、direction、partner；
5. intents；
6. resolutions；
7. birth allocation；
8. death events；
9. entity、environment、information、social 与 knowledge state。

首个失败报告会包含 tick、阶段、数组字段、dtype、shape、最大误差、首差异索引和对应稳定实体 ID。成功 tick 只保留简短状态，避免 100–160 tick 报告过大。

针对已报告案例，在真实 GPU 主机执行：

```bash
scripts/run_reported_gpu_parity_cases.sh
```

或单独运行较短案例：

```bash
PYTHONPATH=src python -m subject_evolution.parity \
  --config configs/mvp_short_k2_exchange.json \
  --output runs/parity_reported_short_exchange_tick160 \
  --ticks 160 \
  --preserve-config-world \
  --world-only \
  --device-backend gpu \
  --require-gpu
```

## 当前验证范围

当前容器无 CuPy/CUDA，不能验证真实混合加速修复。已完成：

- 19 项单元测试通过，1 项真实 GPU 测试明确 skip；
- strict-reference 的模拟 GPU 请求与 CPU 运行 3 ticks 后实体、环境、信息、出生死亡逐数组一致；
- strict-reference clone/paired 分支保持同一 backend 请求语义；
- CPU validation 冒烟 5 ticks 通过；
- NumPy device algorithm 的短阶段 parity 通过；
- 显式 GPU 请求在无设备环境中继续明确失败。

真实 `hybrid-accelerated` 根因尚未声称修复。下一步应基于上述脚本生成的首差异报告，只修改首个离散分歧之前的阶段，而不是继续猜测最终 alive 差异。

## v0.6.4：tick 1 信息源缓冲区首差异修复

真实 GPU 报告已将首差异定位为 tick 1 的 `information.source`：CPU 值
`0.6000000238418579`，GPU 值 `0.6000022888183594`，最大绝对误差
`3.039836883544922e-06`。在该失败之前，prepared index、policy observation、policy
decision、intents、resolutions、birth/death 和 entity state 均一致，因此差异来自本 tick
结束时的稀疏信号场提交，而不是知识交换、策略或出生死亡。

根因是 CPU 与 GPU 分别调用 NumPy/CuPy `ufunc.reduceat`。即使二者使用相同的
`(cell_id, original_order)` 排序，FP32 段内归约树也不保证跨库一致。`source` 是会进入下一
次传播的持久世界状态，不能把这种误差视为普通展示层容差。

v0.6.4 的 hybrid 路径改为：信号计划仍在 CPU 上生成时，使用 NumPy reference
`stable_segmented_sum` 得到每个格点的精确 FP32 总量，只上传唯一的非零格点及总量，然后
在设备上执行无冲突的唯一索引 read/add/write。该提交保持 batch 顺序，与
`InformationSystem.emit_plan()` 逐位一致，同时避免上传完整稠密场。

同一报告中的 `environment.resources` 也已出现约 `3.10e-6` 的状态误差。harvest commit
原先使用同一类 CuPy `reduceat` 归约，因此 v0.6.4 同时将四个资源通道的 harvested totals
改为 CPU reference 归约，再只更新唯一受影响格点。这样修复两个持久场中的同类段内求和差异。

parity 报告中的持久场也改为具名字段：`information-fields.field/source/age` 和
`environment-fields.resources/hazard`，便于后续直接识别首差异。

当前容器仍无 CUDA，因此 v0.6.4 已通过 CPU reference/fake-device 回归，但需要在真实 GPU
上重跑 tick 160。若仍有首差异，下一优先项是环境 update/propagate 中的 CPU/CuPy 数学驱动
与逐点运算顺序；不能通过放宽容差掩盖持久世界状态漂移。

## v0.6.5：与 parity 独立的周期位置不变量修复

用户报告 v0.6.4 后 `mvp_short_k2_exchange` 在真实 GPU 上运行至 tick 1000 未发现 CPU/GPU
偏差。之后 `mvp_small_k2` 在 tick 330 左右触发 `periodic position invariant failed`。位置由 CPU
权威世界提交，GUI 和 hybrid GPU 镜像均不是该坐标的独立结算来源，因此此异常不是新的
information/harvest parity 首差异。

旧移动和出生代码直接对 `float32` 坐标执行 `%=`。NumPy 可将微小负值的周期余数舍入到精确
上界，例如 `-1e-7 % 256 -> 256.0f`。v0.6.5 对初始化、出生和移动统一执行 canonical half-open
wrap，并把舍入得到的上界映射回 0。该修复不放宽 parity 容差，也不改变动作、出生死亡或随机流。


## v0.7.0：K3 稀疏 residual 的 GPU 状态

用户已确认 K2 的 `mvp_short_k2_exchange` 在真实 hybrid GPU 路径运行至 tick 1000 未发现 CPU/GPU 偏差，并确认 v0.6.5 周期位置修复后无问题。K3 在此基础上新增稀疏知识 residual：CPU 从动态知识 arena 构建非零 `(active_row, action_id, residual)`，GPU 仅提交这些稀疏值到 logits，不上传完整 entity-action 矩阵。

本轮容器没有 CUDA，因此只完成编译、CPU reference、配置/状态兼容、稀疏计划和 fake-device 单元测试。K3 的真实 CuPy policy/action parity 尚未声称完成。正式硬件验收应比较 `genetic_logits`、`knowledge_logits`、combined action、intent、birth/death 和 checkpoint，并继续要求离散字段逐位一致。

## v0.8.0 K4 说明

K4 候选主体图实现为 CPU authority/host diagnostic 层，只读取已经提交的实体、群组、谱系、知识和策略影响状态，不参与 GPU policy、intent、resolution 或 commit。CPU 上 K3 exchange 与 K4 tracking 的全部共同世界状态逐数组一致。

当前容器没有 CUDA，因此没有执行真实 GPU 上的 K4 诊断输出与性能测试。K4 不改变行动语义；剩余 GPU 风险集中在宿主侧稀疏审计数据传回、低频统计开销及文件输出，不应据此声称完整设备驻留世界循环已经实现。

## v0.10.0 可变潜知识 parity 边界

潜路由采用 CPU-reference 量化 + backend integer batch：五维后果、四维局部状态和 knowledge-use strength 在公开边界量化；router gene 使用 power-of-two clipped-linear 映射；变长投影、路由和聚合均为有界整数运算。这样避免 `tanh`、除法或 GEMM 归约的数值差异直接跨过动作边界。

旧 hybrid GPU path 构造知识 plan 后未传入 `policy.decide()` 的遗漏已修复。真实 CuPy 潜路由多 tick parity 因当前环境无 CUDA尚未验证；`strict-reference` 仍是正式科学运行的后端语义。

## v0.11.0 L2 非线性潜路由 parity 边界

L2 不调用 `tanh`、`exp` 或其他 CPU/CUDA 实现可能不同的激活。第一层 pre-activation、integer hard-tanh、第二层输出、副本可靠性聚合和最终 residual 均为有界整数运算；输入语义在 CPU reference 边界量化。

L2 保留完整 L1 路由前缀并在同一 batch 上同时计算 L1 shadow，parity 报告可同时比较 genetic logits、L1 shadow logits/action、L2 knowledge logits/action 与最终 action。当前容器无 CUDA，真实 CuPy 多 tick L2 world parity 尚未验证；不能仅依据 NumPy 后端中立测试声称硬件 parity 已完成。


## v0.13.0 工作记忆与稀疏选择 parity 边界

工作记忆状态、prediction error、观察差、遗传增益和 hard clip 均在 CPU-reference 定点边界计算并保存为 `int16`。该状态在后果提交后更新，只影响下一 tick。

稀疏选择不使用全局类别 embedding、Softmax 或浮点 Top-k。Query、Key、可靠性缩放和分数均为整数；稳定排序键为 `(-score_q, copy_id, content_id)`。首版 hybrid 路径由 host authority 构造临时 workset，再允许设备批量执行选中副本的 L1/L2 整数路由。

Parity 报告现包含 working-memory entity state、knowledge-policy-plan、selection IDs/scores、genetic/L1/L2/memory-free actions。当前容器无 CUDA，因此只完成 CPU 与模拟设备测试；真实 GPU 上仍须验证 host/device 同步、选中 workset、路由成本扣费和多 tick world state。
