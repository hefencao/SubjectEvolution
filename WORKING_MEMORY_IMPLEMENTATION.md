# v0.13.0 量化工作记忆实现说明

## 定位

`quantized-working-memory-v1` 是一个可关闭、可遗传、可恢复的短期状态机制。它不是外部训练的控制器，也不读取全局 reward、未来状态或设计者定义的类别语义。

工作记忆在本 tick 的动作和五维局部后果完成提交后更新，并从下一 tick 开始进入潜知识路由。这样不会用尚未发生的结果影响当前决策。

## 权威状态

每个实体新增两个 checkpointable SoA 数组：

- `working_memory_q[capacity, 4]`：`int16` 记忆状态；
- `working_memory_previous_observation_q[capacity, 4]`：上次公开状态。

公开输入仍只有能量比例、完整性、繁殖条件和稀缺度四维。更新还读取上一动作的预期五维后果与已提交实际五维后果之差。

## 更新语义

每个记忆维度具有四个遗传参数：衰减、预测误差增益、观察变化增益和偏置。五维预测误差与四维观察变化通过固定、无语义标签的确定性 ±1 投影进入四维状态。

所有状态、增益和累加均在定点/整数边界执行；激活是 hard clip，不使用 `tanh`、`sigmoid` 或 `exp`。达到上限的维度被记录为 saturation。

## 成本和预算

工作记忆更新请求能量：

```text
base + width × per_dimension + saturation_count × per_saturation
```

按实体执行 all-or-none 审核。能量不足时保留旧记忆状态，不提交建议更新，并记录 requested/committed/rejected energy。

## 审计

新增 `knowledge_working_memory.csv`，记录：

- 更新前、建议和提交后的量化状态；
- 当前观察与观察差；
- 五维 prediction error；
- saturation 与 active dimensions；
- 请求/提交能量和接受标志；
- 同一知识路由下，零记忆 shadow 与实际记忆动作是否不同。

K4 将已支付的 memory computation cost 按宿主持有内容的实际 encoded bytes 归因；无内容可归因的部分显式进入 unattributed 计数。

## 科学边界

- 模块默认关闭；
- 不改变知识内容、复制容量或谱系；
- 不提供自然语言语义维度；
- 30-tick 单 seed 结果只证明状态机制生效和可复现，不证明适应优势。
