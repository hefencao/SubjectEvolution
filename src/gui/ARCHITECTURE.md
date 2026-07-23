# 高性能生态游戏运行时架构

## 1. 核心目标

该架构同时满足两类需求：

1. 保留原 Python 仿真的科学语义、确定性和 CPU/GPU 路径。
2. 提供可扩展的娱乐化表现层，使其能发展为游戏中的社会循环、事件系统和叙事系统。

关键原则是 **双世界、单向默认**：

```text
Python 权威生态世界
        │
        │ 只读快照
        ▼
共享内存三缓冲
        │
        ▼
C++ 展示世界 / 社会循环 / 叙事事件
```

默认不存在 C++ 到 Python 的状态写回。因此：

- 掉帧不会改变仿真结果。
- 社会循环故障不会破坏科学输出。
- C++ 可以使用不同的表现帧率和插值策略。
- 娱乐逻辑可以快速迭代。

## 2. 分层

### 2.1 Python Simulation Authority

负责：

- 环境资源和危险场更新
- 信息传播
- 空间索引
- 策略计算
- 动作意图和冲突裁决
- 世界提交
- 出生、死亡和群体更新
- checkpoint、metrics 和实验有效性

该层不依赖窗口系统。

### 2.2 Snapshot Extraction

`eco_shm_bridge.py` 在 `step()` 完成后采集：

- 四通道资源场
- hazard
- 存活实体的连续坐标和速度
- 能量、完整度、生育度、年龄、代际
- lineage 和 group
- 上一步 action、target 和 success

只采集展示和社会循环所需数据，不序列化 genotype、memory 等大数组。

### 2.3 Shared Memory Transport

文件结构：

```text
FileHeader, 256 bytes
Slot 0
  SlotHeader, 64 bytes
  resources[4, grid_y, grid_x], float32
  hazard[grid_y, grid_x], float32
  entities[max_entities], EntitySample
Slot 1
Slot 2
```

发布协议：

```text
1. 选择非当前槽位
2. 清除槽位提交序列号
3. 写环境和实体有效负载
4. 写槽位元数据与相同的 begin/end sequence
5. 最后写全局 published_slot / published_sequence / tick
```

读取协议：

```text
1. 读取全局发布信息
2. 读取槽位头
3. 复制有效负载
4. 再次读取槽位头和全局发布信息
5. 任一序列不一致则丢帧重试
```

这不是磁盘持久化格式，而是同机实时传输格式。

### 2.4 C++ Ingest Thread

接收线程只做：

- 检查共享文件
- 读取最新序列
- 校验布局和边界
- 复制到复用的 `Frame`
- 与主线程交换 pending frame

主线程不直接访问变化中的 mmap 数据。

### 2.5 GPU Presentation

环境：

- 把选定资源通道和 hazard 合成 RGBA
- 每个新快照只更新一次纹理
- 最近邻采样，保持网格清晰

实体：

- 使用 `rlgl` 批量提交四边形
- 同一批次内按 group、energy、integrity 着色
- 不为每个实体产生 draw call
- 速度向量仅在实体数较低或用户显式开启时绘制

进一步升级路径：

- 将实体记录直接上传到持久映射 VBO
- 顶点着色器读取位置和属性
- `glDrawArraysInstanced`
- 大规模实体使用视口裁剪和 level-of-detail
- 超过 1M 实体时按空间块进行 GPU culling

### 2.6 Entertainment Social Loop

C++ 侧使用稳定 `entity_id` 作为身份键。

每个主体保存有限状态：

```text
reputation
stress
belonging
current_group
last_seen_tick
```

关系边只在实际互动时创建：

```text
pair(entity A, entity B)
trust
familiarity
last_interaction_tick
```

社会循环由以下事件驱动：

```text
出生 → 身份进入
接近 → 相遇与熟悉
分享 → 信任与声誉
信号 → 传闻
繁殖 → 家族叙事
群体变化 → 归属变化
逃跑 → 压力
死亡 → 身份退出
```

关系图是稀疏的，并定期清理长期无互动边。不会进行 O(N²) 全体比较；
邻近相遇使用空间哈希，并限制单格比较数量。

## 3. 游戏化反馈通道

当前压缩包故意不实现控制回写。正式游戏化时建议增加独立协议：

```text
eco_command.bin
```

命令示例：

```text
SetNarrativeGoal
SpawnVisualQuest
AdjustEntertainmentAffinity
RequestGroupEvent
ApplyEntertainmentController
```

约束：

1. Python 只在 `experiment_mode == "entertainment"` 时消费。
2. 命令进入控制提案/仲裁阶段，不能绕过 intent 和 commit。
3. 每条命令带 tick、command_id、主体 ID 和来源。
4. 科学模式下拒绝并记录。
5. 展示效果和仿真状态修改必须分开。

## 4. 线程模型

```text
Python process
  simulation thread
    step
    snapshot pack
    mmap publish

C++ process
  ingest thread
    mmap verify/copy
    publish pending frame

  main/render thread
    consume latest frame
    update social loop
    update environment texture
    render at display refresh rate
```

社会循环当前运行在主线程，只在新快照到达时更新。规模继续增长时可拆为：

```text
ingest → gameplay job queue → render snapshot
```

## 5. 帧率建议

### 10k 以下实体

- 仿真快照：30–60 Hz
- 渲染：60–144 Hz
- 可显示速度、关系线和事件标签

### 10k–200k 实体

- 仿真快照：10–30 Hz
- 渲染：60–144 Hz
- 关系线仅显示选中实体
- 限制邻近比较
- 环境每快照更新一次

### 200k–1M 实体

- 仿真快照：5–15 Hz
- 使用持久映射 VBO 和 instancing
- GPU 视口裁剪
- 社会循环只处理事件和局部空间块
- 远距离实体聚合为密度层

## 6. 数据一致性

共享内存面向“小端、同机、单写者、单读者”。

它使用序列校验而不是阻塞锁。读取失败只意味着丢弃当前帧，不影响仿真。
对于跨机器部署，应替换为：

- QUIC/UDP 快照
- FlatBuffers/Cap'n Proto
- 可靠事件通道 + 不可靠位置通道

协议中的稳定实体 ID 和 tick 仍可保留。
