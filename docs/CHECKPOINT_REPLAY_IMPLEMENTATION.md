# 全世界 checkpoint 恢复与离线反事实重放（v0.9.0）

## 阶段边界

v0.9.0 实现可恢复的完整世界 checkpoint 与离线分支重放。它是实验基础设施，不增加新的世界行为、知识规则或主体性判定。

旧的 `checkpoint_XXXXXXXX.npz` 保留为分析快照，但它只包含部分活跃实体和诊断数组，不能恢复完整模拟。新的 `checkpoint_XXXXXXXX.sechk` 使用 `subject-evolution-full-checkpoint-v1`，用于精确继续运行和从共同历史创建反事实分支。

## 保存内容

完整 checkpoint 保存：

- 完整固定容量实体数组、free pool、下一实体 ID 与版本；
- 环境资源、hazard 与空间反转状态；
- 信息 field/source/age、待处理 direct messages；
- 信号调度器中尚未 flush 的批次；
- 空间索引的当前排序和 cell 分段；
- SocialSystem 的关系、信任、熟悉度、衰减 tick、群组与方向；
- body、lineage、social candidate subject graph；
- K1–K4 知识目录、副本、局部统计、传输/后果 plan 与候选知识主体累计状态；
- 累计出生死亡、action counts、benefit flows 和繁殖拒绝计数；
- lagged benefit boundary；
- evolution progress tracker 的基线和前次窗口状态；
- intervention flags/history、娱乐模式恢复 cohort；
- 当前 tick 的最后 observation、decision、intent、resolution 与 lifecycle plans。

输出 writer、文件句柄和 GPU runtime 不进入 checkpoint。恢复时会创建新的输出目录和 writer，并在所请求后端上重建 runtime，然后把 host-authoritative 世界状态同步到设备。

## 文件格式与信任边界

`.sechk` 是 ZIP 容器，包含：

- `metadata.json`：schema、项目版本、tick、配置 SHA-256、状态 SHA-256、原执行后端；
- `state.pkl`：项目内部 Python 状态。

状态载荷使用 pickle，因此只能加载本项目自己生成、来源可信的 checkpoint。它不是安全的第三方交换格式。加载时会检查 schema、状态哈希、配置哈希和 tick 一致性。

完整 checkpoint 默认关闭，因为文件明显大于旧 NPZ。配置：

```json
{
  "run": {
    "full_checkpoint_enabled": true,
    "checkpoint_period": 10
  }
}
```

启用后，每个 checkpoint period 同时输出 `.npz` 和 `.sechk`。

## 继续运行

使用通用 CLI：

```bash
python -m subject_evolution.cli \
  --resume-checkpoint runs/source/checkpoint_00000010.sechk \
  --output runs/resumed \
  --until-tick 20 \
  --backend cpu
```

或专用 replay CLI：

```bash
python -m subject_evolution.replay \
  --checkpoint runs/source/checkpoint_00000010.sechk \
  --output runs/resumed \
  --until-tick 20 \
  --backend cpu
```

`--until-tick` 是绝对 tick。允许延长 checkpoint 内嵌配置的 horizon，但不能早于 checkpoint tick。

## 离线配对反事实

```bash
python -m subject_evolution.replay \
  --checkpoint runs/source/checkpoint_00000010.sechk \
  --output runs/paired_reverse \
  --until-tick 20 \
  --intervention reverse-environment \
  --backend cpu
```

baseline 和 intervention 从同一个磁盘 checkpoint 恢复，保留 seed、稳定 ID、随机 stream 与全部 K1–K4 状态。intervention 默认在 checkpoint tick 应用，也可显式设置更晚的绝对 `--intervention-tick`。

## 输出与 provenance

恢复运行新增：

- `replay_provenance.json`；
- run manifest 中的 `checkpoint_lineage`；
- `event_log_scope = post-checkpoint`。

累计世界计数和 K1–K4 状态会恢复，但新输出目录中的逐事件日志只记录 checkpoint 之后发生的事件。checkpoint 之前的日志不复制进新目录；其历史影响已包含在累计状态和候选 tracker 中。

从恢复运行再次保存 checkpoint 时，checkpoint lineage 会继续保留。paired clone 也会把同一 lineage 写入 baseline 与 intervention manifest。

## 确定性验证

短验证使用 CPU、seed 10001、256 初始实体、20 ticks，在 tick 10 保存完整 checkpoint：

- 连续运行到 tick 20；
- 从 tick 10 checkpoint 恢复并运行到 tick 20；
- 两者完整语义状态逐数组/逐字段完全一致；
- tick 15 与 tick 20 的全部共同非计时 metrics 完全一致。

另将磁盘恢复分支与同 tick 的内存 clone 分支比较，baseline 和 intervention 均完全一致。

## 限制

- `.sechk` 当前与 Python 类定义及项目版本耦合，不是长期稳定的语言无关格式；
- 旧 `.npz` 不能自动升级为完整 checkpoint；
- 当前只正式支持项目内置 deterministic CPU/GPU conflict resolver；
- 本容器没有 CUDA，真实 hybrid GPU 的保存/恢复同步尚未在本轮硬件验证；
- 完整 checkpoint 可能很大，因此默认 opt-in；
- event logs 是 post-checkpoint 范围，不是将源 run 的日志物理拼接到恢复目录。
