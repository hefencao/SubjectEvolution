# Renderer Architecture v14

## Public API

```text
include/eco/renderer.hpp
```

仅暴露：

- 模式与选项；
- RenderDetail；
- diagnostics/group summaries/environment probe；
- OverlayBudget/OverlayUsage；
- RenderPerformance；
- WorldRenderer 公共行为。

大型容器不再出现在公共头文件中。

## Internal state

```text
render/renderer_state.hpp
```

### EnvironmentCache

- GPU heatmap texture；
- 资源标尺；
- 自适应标尺；
- 时间滤波资源和 hazard；
- 上一环境帧。

### ObservationCache

- 当前/上一实体位置；
- 生命周期和行为事件；
- FrameDiagnostics；
- 观察 tick。

### GroupCache

- GroupBehaviorSummary；
- 群体中心轨迹；
- 轨迹采样 tick。

### StreamSignature

- tick；
- grid；
- world extent；
- entity capacity。

用于识别新流或回退流。

## RenderContext

```text
renderer_context.cpp
```

每次 draw 只构建一次，包含：

- 连续 RenderDetail；
- BehaviorWeights；
- 当前世界视口；
- inverse zoom；
- selected entity/group；
- OverlayBudget。

`renderer_draw.cpp` 不再重复扫描选中实体、重复计算视口边界或分别生成图层预算。

## Frame lifecycle

```text
receive complete frame
  -> observe_frame
       -> detect stream reset
       -> update entity/group/event caches
       -> record observe timing
  -> update_heatmap when dirty
       -> record heatmap timing
  -> draw
       -> build RenderContext
       -> reset OverlayUsage
       -> render bounded layers
       -> record draw timing
```

## Overlay policy

所有可选叠加层共享同一屏幕空间策略：

- Macro：群体和趋势优先，实体/事件预算低；
- Medium：稳定抽样实体，群体/动作/轨迹共同受限；
- Micro：实体细节增加，但关系和事件仍有硬上限；
- 选中对象可以超过普通预算一个单位，保证始终可见。

## Future modules

下一步建议拆分：

```text
renderer_draw_agents.cpp
renderer_draw_groups.cpp
renderer_draw_selection.cpp
```

当 `renderer_draw.cpp` 再次超过约 900–1000 行时再拆，不应提前制造过多小文件。
