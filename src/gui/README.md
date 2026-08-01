# Eco Game Runtime

这是一个面向高性能娱乐化展示和游戏社会循环的伴生运行时。

它不把原 Python 仿真重写成游戏逻辑，而是维持以下边界：

- Python `Simulation`：环境、策略、动作裁决、出生、死亡和科学数据的权威来源。
- 共享内存快照：同机传输，只保留最新帧，渲染落后时不阻塞仿真。
- C++ Runtime：实时渲染、稀疏社会关系、声誉、群体归属、传闻和事件表现。
- 未来控制回写：必须使用独立命令通道，并只在 entertainment 模式启用。

默认启动 GUI 会显示配置选择页：从项目 `configs/` 目录选择 JSON，选择 CPU、GPU
或 auto 后直接启动 Python 仿真，并连接到它创建的共享帧流。结果保存在
`runs/gui_<配置名>_<时间戳>/`。不再需要先在另一个终端启动 CLI。

若只想查看已经运行的共享帧流，请使用 `--stream`：

```bash
./build/eco_game_runtime --stream ../eco_live.bin
```

可用 `--project-root <路径>`、`--config-dir <路径>` 或 `--python <可执行文件>`
覆盖默认的项目、配置和 Python 解释器位置。

## 目录

```text
eco_game_runtime/
├─ ARCHITECTURE.md
├─ README.md
├─ CMakeLists.txt
├─ include/eco/
│  ├─ mapped_file.hpp
│  ├─ protocol.hpp
│  ├─ renderer.hpp
│  ├─ shared_reader.hpp
│  └─ social_loop.hpp
├─ src/
│  ├─ main.cpp
│  ├─ mapped_file.cpp
│  ├─ renderer.cpp
│  ├─ shared_reader.cpp
│  └─ social_loop.cpp
├─ python/
│  ├─ eco_shm_bridge.py
│  ├─ example_launch.py
│  └─ integration_snippet.py
└─ tests/
   ├─ protocol_layout_test.cpp
   └─ test_python_layout.py
```

## 性能设计

共享快照使用三槽位、无锁、只保留最新帧的内存映射文件：

- Python 总是写非当前槽位。
- 完成有效负载后，再提交槽位序列号。
- 最后发布全局槽位号和序列号。
- C++ 在复制前后校验序列号，发现写入竞争则丢弃该帧。
- 仿真线程不等待 C++。
- C++ 接收线程、主线程和待显示帧形成三缓冲交换，稳定运行后不反复分配大数组。

实体记录为 72 字节。100,000 个实体约为 6.87 MiB/帧：
20 Hz 快照约 137 MiB/s，适合同机内存映射。渲染保持 60–144 FPS，
快照建议先设置为每 2–5 tick 发布一次。

环境只在收到新快照或切换显示通道时更新纹理。实体采用 `rlgl` 批量四边形，
而不是逐实体提交独立 draw call。

## Python 接入

安装 Python 依赖：

```bash
python -m pip install numpy
```

把 `python/eco_shm_bridge.py` 复制到 `subject_evolution.py` 同级目录。

在创建 `Simulation` 后、调用 `simulation.run()` 前加入：

```python
from pathlib import Path
from eco_shm_bridge import SharedFramePublisher, attach_realtime_publisher

stream_path = Path(__file__).with_name("eco_live.bin")
publisher = SharedFramePublisher.from_simulation(
    simulation,
    path=stream_path,
    every_ticks=2,
)

attach_realtime_publisher(simulation, publisher)

try:
    simulation.run()
finally:
    publisher.close()
```

桥接器读取以下现有状态：

- `simulation.environment.resources`
- `simulation.environment.hazard`
- `simulation.entities.entity_id/alive/x/y/vx/vy/energy/integrity`
- `simulation.entities.fertility/age/generation/lineage_id`
- `simulation.social.group_id`
- `simulation.last_intents`
- `simulation.last_resolutions`

GPU 模式下只下载渲染所需的资源场和危险场，不调用完整 `sync_to_host()`。

## C++ 构建

要求：

- CMake 3.20+
- C++20 编译器
- Git 或可访问 GitHub 的网络环境（未安装 raylib 时由 CMake 固定获取 raylib 5.5）

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release
```

运行：

```bash
./build/eco_game_runtime ../eco_live.bin
```

Windows：

```powershell
.\build\Release\eco_game_runtime.exe ..\eco_live.bin
```

## 操作

- 鼠标滚轮：缩放
- 鼠标中键：平移
- 鼠标左键：选中实体
- `1`–`4`：切换资源通道
- `H`：危险场叠加
- `G`：网格
- `V`：速度向量
- `S`：社会循环面板
- `R`：重置视图

## 社会循环

C++ 娱乐层当前实现：

- 出生、死亡和群体变更事件
- `SHARE` 成功后的信任、熟悉度和声誉变化
- `SIGNAL` 产生带时效的传闻
- `REPRODUCE`、`FLEE`、`HARVEST` 的表现层状态变化
- 空间邻近相遇产生稀疏关系边
- 每实体关系数量由实际互动自然形成，不构建全连接图
- 陈旧边周期清理
- 群体归属、压力、声誉和平均信任统计

这些数据不会写回原模拟。要让社会循环影响游戏角色行为，应另建
`eco_command.bin` 命令环，并在 Python entertainment 模式的控制仲裁前消费。
不要让展示层直接改写 `entities` 数组。
