# 生态模拟演化项目交接报告

**交接基线：GUI v19；自本报告起暂停 GUI 常规功能开发，工作重心转向 Python/CUDA 模拟演化。**  
**归档日期：2026-07-24**

## 1. 执行摘要

项目已经具备一套可用的“大规模生态仿真观察终端”：Python/CUDA 负责权威模拟状态，C++20/raylib GUI 通过同机共享内存读取快照，提供连续 LOD、环境场、实体行为、群体分析、社会观察、选择/跟随、暂停观察，以及 v19 的 GPU 实体实例化渲染。

GUI 已经足以支持下一阶段的模型诊断。继续增加 GUI 功能的边际收益开始低于模拟语义、演化机制、可重复性和 CPU/GPU 一致性的价值，因此本阶段正式冻结 GUI 的常规演进。后续 GUI 改动仅限：

1. 阻塞模拟调试的缺陷；
2. 共享协议兼容性问题；
3. 明确由 profiling 证明的性能瓶颈；
4. 为新的模拟变量提供最小必要观察入口。

当前推荐基线是 `eco_game_runtime_gui_v19_full.zip`。v19 在 v18 的模块化、统一预算与性能计时基础上，为抽样后的实体标记增加 OpenGL 3.3/4.3 instancing；CPU rlgl 批处理仍是完整回退路径。该 GPU 升级没有改变 Python 仿真、共享内存协议、LOD 语义或群体观察逻辑。

## 2. 项目目标与边界

### 2.1 目标

项目希望实现可扩展的生态—演化—社会模拟，并最终支持两类使用方式：

- **科学/分析模式**：强调确定性、可重复性、干预和反事实、指标可解释性、CPU/GPU 语义一致；
- **娱乐/游戏模式**：在不污染科学状态的前提下，利用群体、谱系、资源危机、迁徙和社会循环形成可观察的涌现叙事。

### 2.2 权威状态边界

Python/CUDA 模拟是唯一权威状态源。C++ GUI 默认只读：

```text
Python / NumPy or CuPy simulation
        │
        │ publish immutable frame snapshot
        ▼
eco_live.bin shared-memory triple buffer
        │
        ▼
C++ SharedReader → Frame
        │
        ├─ environment visualization
        ├─ sampled entities and behavior
        ├─ group observation / trails / picking
        ├─ inspector and performance telemetry
        └─ C++ entertainment-oriented social display state
```

C++ 的 `SocialLoop` 是展示和娱乐层派生状态，不应被自动视为 Python 科学模型的真实社会机制或实验指标。若未来需要 GUI 反向控制仿真，应建立显式命令通道、版本化命令协议和科学/娱乐模式隔离，不能直接从渲染代码修改模拟数组。

## 3. 当前运行流程

默认 GUI 启动流程保持如下：

1. 打开配置选择页；
2. 从项目 `configs/` 选择 JSON；
3. 选择 `cpu`、`gpu` 或 `auto`；
4. GUI 启动 Python 仿真；
5. 结果写入 `runs/gui_<配置名>_<时间戳>/`；
6. GUI 连接该运行目录中的 `eco_live.bin`。

查看已运行共享流：

```bash
./build/eco_game_runtime --stream ../eco_live.bin
```

仍支持：

```text
--project-root
--config-dir
--python
--stream
```

## 4. 共享内存协议

v19 公共协议仍为版本 1：

- magic：`ECOGAME1`；
- little-endian；
- 默认 3 个槽位；
- `FileHeader` 256 字节；
- `SlotHeader` 64 字节；
- `EntitySample` 72 字节；
- 环境为四通道资源场加 hazard；
- 实体包含 ID、group、lineage、target、位置、速度、energy、integrity、fertility、age fraction、generation、action 和 success。

发布端写非当前槽，完成 payload 后提交槽位序列，最后更新全局发布位置；读取端在复制前后验证序列。一旦检测到竞争，读取器丢弃该快照而不是阻塞 Python。

### 4.1 协议变更规则

后续模拟开发若新增字段，必须：

- 提高协议版本；
- 同步 Python writer、C++ `protocol.hpp`、布局测试和兼容错误信息；
- 优先增加低频聚合块或可选扩展区，避免无限扩大逐实体样本；
- 保留旧 GUI 对旧协议的明确失败或兼容路径。

## 5. GUI v19 架构

### 5.1 公共接口与状态

`WorldRenderer` 使用 PImpl，公共头文件只暴露稳定观察 API，内部状态位于 `render/renderer_state.hpp`。关键内部缓存包括：

- `EnvironmentCache`；
- `ObservationCache`；
- `GroupCache`；
- `StreamSignature`；
- GPU 实例化缓存。

统一 `RenderContext` 在每帧集中计算 camera、viewport、连续细节权重、选择/聚焦状态和叠加层预算。

### 5.2 编译单元

```text
renderer.cpp                 compatibility facade
renderer_context.cpp         continuous detail and shared overlay budgets
renderer_core.cpp            public API, lifecycle, stream epochs
renderer_environment.cpp     resource/hazard texture, filters and probes
renderer_observation.cpp     diagnostics, groups and temporal observation
renderer_groups.cpp          group trails, geometry, landmarks and picking
renderer_draw.cpp            layer composition and CPU marker fallback
renderer_gpu.cpp             optional GL3.3/4.3 agent instancing
renderer_internal.cpp        math, colors, batching and behavior glyphs
render/renderer_internal.hpp internal declarations
render/renderer_state.hpp    renderer-owned caches
```

正式 CMake 目标必须包含上述实现，尤其是 v14 新增的 `renderer_context.cpp` 和 v19 新增的 `renderer_gpu.cpp`。`renderer_internal.hpp` 与 `renderer_state.hpp` 同处 `render/`，正确引用为：

```cpp
#include "renderer_state.hpp"
```

### 5.3 观察功能

当前已具备：

- 连续 Macro/Medium/Micro 细节权重，而不是纯硬切换；
- Composite、Resource、Gradient、Hazard、Population、Resource Delta 环境视图；
- Stable/Responsive/Instant 环境和行为时间滤波；
- 稳定屏幕空间实体抽样；
- 出生、死亡、采集、繁殖和动作图形；
- 群体稳定视觉身份、行为构成、空间椭圆、轨迹和拾取；
- group focus、实体/群体跟随、环境探针和关系线；
- F1–F6 观察预设与语义动作过滤；
- `Space` 画面保持、`N` 采样最新帧；
- 统一 OverlayBudget；
- observe/scan/group/heatmap/draw 计时；
- v19 实体 GPU instancing，`U` 切换 auto/gpu/cpu。

### 5.4 GPU 状态

v19 只将“已经由 CPU 完成裁剪和 LOD 抽样的实体标记”转为实例化绘制：一个单位四边形、一个动态 instance VBO、一次 instanced draw。环境合成、观察统计、行为图形、群体覆盖和社会关系仍主要在 CPU 侧。

根据此前实际截图，`draw` 通常不是最大成本，`observe` 与 `heatmap` 更值得优化。因此 CUDA/OpenGL 互操作不应成为近期模拟工作的前置条件。若未来恢复 GUI GPU 工作，优先顺序应是：

1. GPU 环境合成；
2. 可选 OpenGL 4.3 compute blur/gradient/binning；
3. profiling 证明传输成为瓶颈后，才考虑 CUDA/OpenGL interop。

## 6. GUI 迭代成果概览

- v1：基础 C++ runtime、共享协议、共享读取、基础 renderer 和社会显示层；
- v2–v5：LOD、Inspector、事件、Macro 稳定性和 rlgl 顶点/纹理修复；
- v6–v9：环境时间/空间滤波、连续细节、资源枯竭可读性、Medium 预算；
- v10–v12：行为语义、群体轨迹/形状/选择、环境探针；
- v13/13.1：renderer 独立编译单元拆分及 CMake 链接修复；
- v14：PImpl、RenderContext、统一 OverlayBudget、流生命周期和性能计时；
- v15–v17：观察预设、动作过滤、稳定群体颜色、方向修复、行为时间稳定；
- v18：内部 include 修复、观察管线优化、视觉暂停；
- v19：GPU 实体实例化和 CPU 回退。

完整逐版本索引见 `handoff/VERSION_INDEX.md`。

## 7. 已知风险与未完成事项

### 7.1 GUI 风险

1. **真实 GPU 性能未在目标 Windows/CUDA 机器系统测量**：v19 验证使用 raylib 兼容桩，证明 API/state/memory safety，不代表真实驱动加速比。
2. **observe 仍可能是主要成本**：群体匹配、行为平滑和统计都依赖实体扫描。规模继续扩大时需降低分析频率或由模拟端输出有限聚合信息。
3. **heatmap 仍为 CPU 合成**：只有 GUI profiling 明确阻碍模拟诊断时才恢复此项。
4. **共享协议只能表达当前字段**：新的演化基因、物种、性状或生理状态需要协议升级或低频扩展区。
5. **C++ SocialLoop 与科学模型边界容易混淆**：科研报告必须使用 Python metrics，而非 GUI 派生 trust/stress/rumor。
6. **视觉增强不是原始量**：环境亮度包含平滑、自适应标尺和对比增强；原始科学值应读取 Inspector 或模拟输出。

### 7.2 归档完整性说明

本归档包含当前工作区能够找到的所有版本包和直接 diff。不存在独立的“v1 patch”；v1 由初始基线归档代表。部分早期版本没有单独的相邻版本 `.diff`，但 v2–v14 的完整 patch archive 均已保留，足以重建对应版本。具体文件可用性见 `handoff/VERSION_INDEX.md` 和 `FILE_MANIFEST.txt`。

## 8. 模拟源代码现状

归档中的 `current/simulation_reference/subject_evolution_aggregate_snapshot.py` 是当前工作区可取得的约 8,938 行聚合快照。它包含多个原本分拆模块连续拼接的内容和相对导入，**不是保证可直接运行的单模块**。接手模拟工作的首要动作应是从真实项目导出完整的：

```text
src/subject_evolution/
configs/
tests/
```

并以实际 split tree 为权威。聚合快照只用于识别已有设计和避免重复实现。

从快照可确认已有/规划中的模拟结构包括：

- NumPy/CuPy backend 选择及显式 host/device 转换；
- 配置加载和校验；
- CPU `Environment` 与 GPU `DeviceEnvironment`；
- 信息场与直接消息观察；
- 参数化策略、随机上下文和确定性抽样；
- 动作 intent、冲突解析、harvest/share 计划；
- birth/death 计划与提交；
- `EntityState` 和主 `Simulation.step()`；
- group detection/label planning；
- Python `SocialSystem`；
- interventions、paired counterfactual 和 scientific validity；
- candidate subject graph、谱系和 benefit flow；
- metrics/evolution progress tracker；
- Hybrid GPU runtime 与传输统计。

## 9. 转向模拟演化的优先级

### P0：可重复性与科学有效性

在增加新行为前先固定：

- 配置、seed、backend、版本、设备和依赖元数据；
- 同 seed CPU 重复运行逐 tick 或 checkpoint 一致性；
- CPU/GPU 语义一致性及容差政策；
- paired intervention 使用共同随机数；
- 每个指标明确属于原始状态、派生统计还是展示层。

验收标准：同一配置能生成可比较的 run manifest；CPU reference 是清晰的语义基线；GPU 偏差能够定位到具体阶段。

### P0：守恒、边界与生命周期不变量

建立机器可检查的不变量：

- entity ID 唯一，alive/free pool 一致；
- birth/death 提交不重复、不越界；
- energy、integrity、fertility 和资源均满足定义域；
- harvest 不超过可用资源和限额；
- share/benefit flow 的来源、去向和损耗可核算；
- 周期世界位置和空间索引一致；
- group membership、subject graph 与死亡清理一致。

每次 `Simulation.step()` 在 debug/validation 模式输出或断言预算平衡，而不是只依赖最终曲线。

### P1：真正的演化信号

重点回答“哪些性状在什么环境下获得可测的适应优势”：

- 基因型 → 感知/策略参数 → 行为 → 收益 → 生存/繁殖的因果链；
- 突变率、效应分布、遗传约束和代价；
- 谱系多样性、性状方差、有效群体大小和选择差；
- 避免仅靠高 birth/death turnover 制造看似演化的噪声；
- 增加中性对照、无遗传对照和固定策略对照。

最低验收：至少一个预先定义的环境梯度下，已知有利性状能够在重复实验中稳定上升；撤销选择压力后结果相应改变。

### P1：生态动力学与资源反馈

当前观察中资源经常快速衰减至接近零，说明模型侧需要优先验证：

- 资源再生和扩散时间尺度；
- 采集量、移动成本和基础代谢的量纲；
- hazard 与资源是否独立或存在合理耦合；
- 空间斑块是否具有持续性，而非初始化图样；
- 承载力、崩溃、恢复和迁徙是否在合理参数区间出现。

建议建立单资源、无社会、无繁殖的最小生态基准，再逐层打开机制。

### P1：行为决策和冲突解析

逐动作验证：

- move-resource 是否统计上沿可感知梯度移动；
- harvest 的 target/cell 语义是否一致；
- flee 是否响应真实 hazard，而不是固定模板或噪声；
- share/signal 的发送、接收和收益边界可追踪；
- reproduce 的候选排序、配对、资源代价和子代初始化明确；
- rest 必须有可解释的恢复/节约作用。

采用 intent → plan → commit 的阶段性测试，确保动作排序变化不改变本应无关的结果。

### P2：Python 社会和群体机制

科学社会机制应在 Python 中定义，C++ 仅观察：

- relation update 的来源和衰减；
- group detection 的空间/关系阈值；
- group ID 持续性和分裂/合并语义；
- 信息传播与行为改变的因果证据；
- social benefit 与 direct resource/energy flow 的边界。

首先构造 10–100 个实体的可手工验证场景，再扩展到数万实体。

### P2：GPU 语义一致与性能

性能优化顺序：

1. profile 每个 step 阶段；
2. 减少不必要 host/device round-trip；
3. 保持实体和字段长期驻留设备；
4. 仅传递 commit plan 或稀疏观测；
5. 用 CPU reference 和小规模逐阶段对照锁定语义；
6. 再优化 kernel/segmented reduction/排序。

不能以“曲线看起来相似”作为 GPU 一致性的唯一标准。

### P2：实验基础设施

每个正式实验应生成：

```text
run_manifest.json
resolved_config.json
metrics.csv/parquet
scientific_validity.json
event summaries
checkpoints/
logs/
```

支持 seed sweep、参数 sweep、paired intervention、早停规则和自动汇总。GUI run 目录可以继续使用，但实验结果不应依赖 GUI 是否打开。

## 10. 建议的测试矩阵

### 单元测试

- backend selection 和显式转换；
- deterministic RNG stream；
- stable segmented sum；
- cell ID、周期边界和空间索引；
- harvest/share/action conflict；
- birth/death/free pool；
- information propagation；
- group plan 和 relation update；
- candidate subject graph。

### 小世界场景测试

- 1 个实体、1 个资源格；
- 两实体争夺同一资源；
- 两实体 share 成功/失败；
- hazard 梯度上的 flee；
- 周期边界上的资源追踪；
- 一次确定性繁殖和一次确定性死亡；
- 群体分裂与合并；
- 信息信号有/无干预对照。

### 性质/不变量测试

- permutation invariance；
- 批量顺序不改变无冲突动作；
- 总资源/能量预算在已定义损耗内闭合；
- 全部数组有限且满足范围；
- 同 seed 结果稳定；
- checkpoint 恢复与连续运行一致。

### CPU/GPU 对照

按阶段比较，而不是只比较终点：

```text
environment update
field propagation
sensing
policy decision
intent build
conflict resolution
commit
birth/death
social/group update
metrics
```

## 11. 接手者第一周行动清单

### 第 1 天：建立权威基线

- 从真实项目导出 split Python 源码、配置和测试；
- 固定一个 CPU 小规模 reference config；
- 固定一个当前常用大规模 config；
- 记录环境、Python、NumPy/CuPy、CUDA 和 GPU 信息；
- 运行现有测试并归档结果。

### 第 2 天：画出 `Simulation.step()` 数据流

- 列出所有阶段、输入、输出、可变状态和同步点；
- 标注 CPU/GPU resident 数据；
- 标注随机流和 commit boundary；
- 明确哪些指标是科学指标。

### 第 3 天：不变量和最小场景

- 增加 lifecycle、resource、energy、ID/free-pool 断言；
- 创建 1、2、10 实体的确定性场景；
- 验证 checkpoint 恢复。

### 第 4 天：CPU/GPU 阶段对照

- 在小规模配置下逐阶段比较；
- 记录首次差异位置，而不是只看最终 metrics；
- 明确浮点容差与必须逐位一致的离散结果。

### 第 5 天：演化有效性实验设计

- 选择一个单一可解释性状；
- 定义选择压力、对照和预期方向；
- 运行多 seed pilot；
- 检查结果是否来自真实遗传选择，而非初始化或人口瓶颈。

第一周不建议新增 GUI 页面，也不建议直接做 CUDA/OpenGL interop。

## 12. 构建与验收基线

GUI v19 应使用干净构建：

```bash
rm -rf build
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j
ctest --test-dir build --output-on-failure
```

确认目标包含：

```text
renderer_internal.cpp
renderer_context.cpp
renderer_core.cpp
renderer_environment.cpp
renderer_observation.cpp
renderer_groups.cpp
renderer_draw.cpp
renderer_gpu.cpp
```

运行 GUI 时初始建议保留：

```text
U auto
T stable
Y stable
LOD auto
```

GUI 冻结后，只有在新的模拟字段无法通过现有 Inspector、metrics 或离线分析判断时，才增加最小显示功能。

## 13. 归档内容说明

本归档包括：

- v19 完整 GUI 源码（压缩包和展开目录）；
- 当前可得的模拟聚合快照；
- v2–v14 完整版本 patch archive；
- v15–v19 完整源码快照；
- 当前可得的全部直接 `.diff`；
- apply 脚本；
- PATCH_NOTES、MIGRATION、架构和验证文档；
- 初始/早期 runtime 基线归档；
- `FILE_MANIFEST.txt` 和 `checksums/SHA256SUMS.txt`。

归档的目的不是鼓励继续沿历史版本逐层覆盖，而是保存可追溯性。日常开发应从 v19 完整源码或实际主仓库继续。
