# Subject Evolution v0.30

一个以**可审计世界状态、局部交互、遗传策略、动态知识副本、候选主体结构和多元环境**为核心的演化模拟参考实现。

科学核心不引入第二套“生物型危险实体”。具有出生、死亡、策略、关系、记忆或谱系的危险主体，应由现有实体系统分化；环境模块只承载资源、物理危险、死亡痕迹和受限插件字段。

## v0.30 主线转向

v0.30 将工作重心从自然事件执行工具转向两个基础研究层：

1. **主体结构**：不再只看某个 tick 有多少群组，而是按稳定实体身份追踪候选社会结构的形成、延续、消散、分裂、合并与复现。
2. **多元环境**：在多个空间尺度上描述四资源组合、危险、死亡痕迹、环境周转，以及谱系/社会结构实际占据的环境范围与暴露分化。

两层均为纯诊断，默认关闭，不修改策略、行动、群组标签、知识、关系、生命周期或环境场。默认世界轨迹保持兼容。

## 主线配置

新的科学长跑配置：

```bash
python -m subject_evolution.multi_seed \
  --config configs/mvp_short_subject_structure_multienvironment_atlas_longrun.json \
  --seeds 10001,10002,10003 \
  --output runs/subject_structure_multienvironment_multiseed \
  --backend gpu \
  --until-tick 1500
```

该配置保留 v0.29 flagship 的模拟语义，并额外启用：

- `stable-membership-subject-succession-v1`；
- `multiscale-subject-environment-atlas-v1`；
- `2×2`、`4×4`、`8×8` 三种归一化环境尺度；
- long-run analysis v9 和原有 local stress/culture diagnostics。

请求 GPU 时仍使用 `gpu_semantics_mode="strict-reference"`。设备会被验证，但科学世界语义由 CPU reference 路径权威执行。

## 主体结构诊断

每次实际 group refresh 后，诊断层读取：

- 当前 group plan；
- 每个成员的 stable entity ID；
- 上一次 refresh 的候选群组成员集合。

只要前后群组共享至少一个 stable entity ID，就建立一条**观察性继承边**。据此记录：

- formation / dissolution；
- split source / merge target；
- same-token 与 exact-membership persistence；
- 成员加权 predecessor Jaccard；
- 成员继承比例；
- 活跃群组年龄和有效群组数。

这些继承边不写入世界中的 `CandidateSubjectGraph`，也不宣称群组具备本体论上的连续主体身份。

输出：

```text
subject_structure_transitions.jsonl
subject_structure_summary.json
```

## 多元环境图谱

环境图谱在低频 evolution evaluation 点采样权威字段。每个尺度、每个区域的 signature 包含：

```text
四个容量归一化资源均值
hazard 均值
mortality trace 均值
```

图谱报告：

- 环境 signature 有效维数；
- 区域间平均/最大距离；
- 资源空间 CV；
- 相邻评估点的环境周转；
- 实体占据区域的有效数量；
- 谱系和社会群组的环境暴露 association；
- 谱系和社会群组的平均区域跨度。

association 只在至少两个成员的标签上计算，并同时报告 covered fraction，避免大量单体谱系把解释度机械推到 1。

输出：

```text
environment_atlas.jsonl
environment_atlas_summary.json
```

## 多 seed 主体—环境分析

```bash
python -m subject_evolution.structure_environment_analysis \
  runs/subject_structure_multienvironment_multiseed/seed_10001 \
  runs/subject_structure_multienvironment_multiseed/seed_10002 \
  runs/subject_structure_multienvironment_multiseed/seed_10003 \
  --output analyses/subject_structure_multienvironment
```

分析器会把每个环境评估点对齐到此前最近一次 group refresh，计算环境周转、结构继承、split/merge、社会暴露 association 和空间跨度之间的观察性关系，并先按 run/seed 分开，再报告跨 seed 同号方向。

## 协议审计

```bash
python -m subject_evolution.protocol_audit \
  --config configs/mvp_short_subject_structure_multienvironment_atlas_longrun.json \
  --output analyses/protocol_audit
```

v2 审计同时覆盖：

- group label 和 adaptive refresh；
- candidate-subject succession；
- spatial region partition；
- multiscale environment atlas；
- 可选 natural-event anchor selection。

## 安装与快速运行

```bash
python -m venv .venv
source .venv/bin/activate            # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e .

python -m subject_evolution.cli \
  --config configs/smoke_cpu.json \
  --output runs/smoke_cpu \
  --backend cpu
```

CPU reference 只依赖 NumPy。GPU 路径需要与本机 CUDA 主版本匹配的 CuPy。

## 解释边界

- 候选群组继承不是主体身份定理。
- 分裂/合并是成员集合重叠关系，不是生物繁殖或组织法律继承。
- 环境 association 是实现暴露差异，不是环境选择的因果效应。
- 社会结构与环境周转的相关可能共同受到人口瓶颈、迁移、谱系集中和时间趋势驱动。
- 四资源、hazard 和 mortality trace 仍是固定环境 vocabulary；任意环境通道和任意嵌套主体尚未实现。

## 文档

- [当前项目状态](docs/PROJECT_STATUS.md)
- [科学问题与研究债务](docs/SCIENTIFIC_ISSUES.md)
- [架构与提交边界](docs/ARCHITECTURE.md)
- [变更记录](docs/CHANGELOG.md)
- [v0.30 文档](docs/v0.30/README.md)
- [v0.29 group/region/anchor 协议](docs/v0.29/GROUP_REGION_ANCHOR_PROTOCOLS.md)

发行压缩包不包含 `docs/archive`。更早的完整历史保存在旧版本发行包中。
