# v0.33 入口层与 GUI 接口重构

## 范围

本轮不改变世界状态、随机键、行动结算、环境、知识、演化、主体或日志语义。目标是继续收窄入口层，并把用户提供的 `gui_interface` 从孤立示例整理为正式、版本化的外部接口。

## 入口层

规范命令实现迁入：

```text
subject_evolution/commands/run.py
subject_evolution/commands/multi_seed.py
```

历史入口继续有效：

```text
python -m subject_evolution
python -m subject_evolution.cli
python -m subject_evolution.multi_seed
```

`cli.py` 与 `multi_seed.py` 现在各 6 行，只负责兼容转发。`pyproject.toml` 的 console scripts 直接指向规范实现：

```text
subject-evolution
subject-evolution-multi-seed
subject-evolution-gui
```

## 统一 compatibility facade

v0.32 中 35 个顶层兼容模块各自复制相同的 `ModuleType` 转发代码。v0.33 新增：

```text
subject_evolution/_compat.py
```

所有兼容模块通过 `install_facade()` 安装转发。它保留：

- 旧 import path；
- `python -m subject_evolution.<legacy-module>`；
- 对旧模块属性的 monkey patch；
- trusted checkpoint 使用的历史类 module identity。

35 个通用 facade 的总行数由 770 降至 210。四个主要入口文件 `cli.py`、`multi_seed.py`、`simulation.py`、`__main__.py` 从 328 行降至 30 行。

## GUI 分层

规范实现位于：

```text
subject_evolution/interfaces/gui/
├── protocol.py
├── publisher.py
├── reader.py
├── attachment.py
└── runner.py
```

兼容路径位于：

```text
subject_evolution/gui_interface/
```

运行时和 domain package 不导入 GUI interface。Python 世界保持权威，GUI 只能读取发布帧，不能反馈或修改 scientific state。

## 用户提供代码的整合

保留原 bridge 的核心协议：

- `ECOGAME1` magic；
- protocol version 1；
- 256-byte file header；
- 三缓冲 latest-frame-only；
- 64-byte slot header；
- 72-byte entity record；
- resources、hazard、entities 固定顺序；
- commit sequence 在 payload 写完后发布。

在此基础上补充：

- 原子写入的协议 sidecar manifest；
- `running` / `closed` producer 状态；
- reference `SharedFrameReader`；
- double-checked sequence reader；
- attachment context manager；
- 重复挂载拒绝；
- config 和 trusted checkpoint 两种 GUI 启动源；
- `until-tick` 与 GPU semantics override；
- 新旧 GUI import/CLI 路径。

## 科学边界

共享帧发布是 observation-only：

- GUI 可以丢帧；
- GUI 不阻塞权威世界；
- GUI 不产生 checkpoint；
- GUI 不能修改 mmap；
- GUI 数据不得替代完整科学日志；
- hybrid GPU 模式下发布需要 host snapshot，可能产生设备到主机传输开销。

## 验证

- 全量测试：161 passed，1 skipped；
- 入口 module `--help` smoke 全部通过；
- GUI publisher/reader round-trip 通过；
- 重复 attachment 拒绝通过；
- GUI runner final-frame smoke 通过；
- GUI attached 与无 GUI 30-tick 权威状态零差异；
- 非计时核心/环境输出逐字节一致；
- v0.32→v0.33 非计时 metrics 和权威 state 零差异；
- v0.32 tick-15 checkpoint 由 v0.33 续跑到 tick 30 与连续 v0.33 一致。
