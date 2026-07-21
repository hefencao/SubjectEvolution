# 统一采样API与信息误差规范

版本：v0.2  
定位：所有不确定性、信息误差、注意力限制和行为随机性的唯一入口。

---

## 1. 设计目标

统一采样系统必须同时满足：

- GPU并行；
- 无状态；
- 可复现；
- 可审计；
- 可替换分布；
- 可进行消融；
- 不因线程顺序变化；
- 不因新增日志改变随机轨迹；
- 支持CPU参考实现。

采样算法属于模拟世界规则的一部分，不是可以随意更换的底层细节。

---

## 2. 随机键

```cpp
struct RandomKey {
    uint64_t run_seed;
    uint64_t tick;
    uint32_t simulation_phase;
    uint64_t subject_id;
    uint32_t stream_id;
    uint32_t draw_index;
};
```

### 2.1 键语义

- `run_seed`：实验种子；
- `tick`：世界时间；
- `simulation_phase`：当前执行阶段；
- `subject_id`：采样所属主体或事件ID；
- `stream_id`：随机机制类别；
- `draw_index`：同一机制中的第几次抽样。

### 2.2 事件采样

不存在自然主体ID时，使用稳定事件ID或由稳定输入生成的哈希。不得使用GPU数组索引代替稳定ID。

---

## 3. 随机流注册

建议固定：

| stream_id | 名称 |
|---:|---|
| 1 | ENV_RESOURCE |
| 2 | ENV_CLIMATE |
| 3 | ENV_DISASTER |
| 10 | SIGNAL_EMISSION |
| 11 | SIGNAL_CHANNEL |
| 12 | SIGNAL_DETECTION |
| 13 | SIGNAL_DECODING |
| 14 | MEMORY_NOISE |
| 20 | NEIGHBOR_SAMPLE |
| 21 | ATTENTION_SAMPLE |
| 22 | MESSAGE_CAPACITY |
| 30 | POLICY_ACTION |
| 31 | POLICY_EXPLORATION |
| 32 | ACTION_EXECUTION |
| 40 | CONFLICT_RESOLUTION |
| 50 | REPRODUCTION |
| 51 | MUTATION |
| 52 | GENE_EXPRESSION |
| 60 | DISEASE |
| 70 | RELATION_UPDATE |
| 71 | GROUP_FORMATION |
| 80 | CAUSAL_INTERVENTION |
| 90 | HERO_LEARNING |

注册表必须版本化。删除流时保留编号，不重新分配。

---

## 4. API分层

### 4.1 基础随机位

```cpp
uint32_t random_u32(RandomKey key);
uint64_t random_u64(RandomKey key);
float uniform01(RandomKey key);       // [0,1)
double uniform01_double(RandomKey key);
```

### 4.2 基础分布

```cpp
bool bernoulli(RandomKey key, float p);
int categorical(RandomKey key, Span<float> probabilities);
float normal(RandomKey key, float mean, float stddev);
float truncated_normal(RandomKey key, float mean, float stddev, float lo, float hi);
float lognormal(RandomKey key, float mu, float sigma);
int poisson(RandomKey key, float lambda);
float exponential(RandomKey key, float rate);
float gumbel(RandomKey key, float location, float scale);
```

### 4.3 集合抽样

```cpp
sample_without_replacement(
    RandomKey base_key,
    Span<Item> items,
    int k
);

weighted_sample_without_replacement(
    RandomKey base_key,
    Span<Item> items,
    Span<float> weights,
    int k
);
```

### 4.4 策略动作

```cpp
ActionSample sample_action(
    RandomKey key,
    Span<float> logits,
    Span<bool> action_mask,
    float temperature,
    SamplingMethod method
);
```

输出：

```text
ActionSample
{
    action_index
    probability
    entropy
    normalized_temperature
    method
    key
}
```

---

## 5. 推荐随机算法

底层可采用：

- Philox；
- Threefry；
- 其他经过验证的counter-based RNG。

要求：

- 以随机键为counter和key；
- CPU/GPU有一致实现；
- 不依赖可变内部状态；
- 通过基础统计测试和并行相关性测试。

不得直接在业务代码中使用语言标准库随机函数或GPU线程本地可变RNG状态。

---

## 6. 信息传播误差模型

### 6.1 源编码

\[
m=\operatorname{Encode}(s,\theta_{\text{source}})+\epsilon_s
\]

参数：

- 编码精度；
- 压缩率；
- 表达能力；
- 欺骗倾向；
- 发送功率；
- 符号词典版本。

源误差应拆成：

- 无意噪声；
- 系统偏差；
- 有意操纵。

### 6.2 信道传播

\[
m'=\operatorname{Channel}(m,d,T,C,\tau)+\epsilon_c
\]

参数：

- 距离；
- 地形；
- 气候；
- 遮挡；
- 延迟；
- 干扰；
- 多信号叠加；
- 反射；
- 信号寿命。

建议检测概率：

\[
p_{\text{detect}}=
\sigma(
\alpha\cdot strength
-\beta\cdot noise
-\gamma\cdot obstruction
+\delta\cdot sensitivity
)
\]

通过Bernoulli采样决定是否检测。

### 6.3 接收与解码

\[
o_i=\operatorname{Decode}(m',\theta_i^{sensor},\theta_i^{belief})+\epsilon_i
\]

接收属性：

- 灵敏度；
- 方向；
- 当前能量；
- 注意力；
- 年龄；
- 经验；
- 信任；
- 身份；
- 先验；
- 传感器损伤。

### 6.4 记忆误差

记忆保留概率可表示为：

\[
p_{\text{retain}}=\exp(-\lambda\Delta t)\cdot salience
\]

需要支持：

- 遗忘；
- 覆盖；
- 错误归因；
- 重复强化；
- 群体共识改写；
- 情绪或内部状态加权。

---

## 7. 误差组合规则

不得把所有噪声直接相加成一个高斯项。应区分：

- 检测失败：无观察；
- 数值误差：观察值偏移；
- 分类错误：被识别为另一类别；
- 来源错误：信息归因错误；
- 延迟：观察旧状态；
- 截断：只看到部分邻居；
- 伪造：接收到人为构造信息；
- 记忆重构：历史被错误修改。

观察结构中必须有：

- value；
- mask；
- age；
- confidence；
- source estimate；
- corruption flags。

---

## 8. 邻居采样

邻居抽样直接塑造主体可见社会。

支持方法：

1. 最近邻；
2. 均匀随机；
3. 距离加权；
4. 信号强度加权；
5. 关系强度加权；
6. 类型分层；
7. 新旧关系混合；
8. 蓄水池抽样；
9. 重要性抽样。

推荐混合方案：

- 固定保留最近`K_near`；
- 固定保留最强关系`K_relation`；
- 其余候选中随机抽样`K_explore`。

这样兼顾物理相关性、社会记忆和新关系探索。

必须记录：

- 候选总数；
- 被采样数量；
- 方法；
- 权重；
- 覆盖率；
- 截断率。

---

## 9. 注意力采样

传感器检测到的信息不等于进入决策。

注意力权重可由：

- 新颖性；
- 威胁；
- 资源相关性；
- 来源信任；
- 社会身份；
- 当前内部状态；
- 最近关注历史；

共同决定。

注意力采样必须与信号检测分离，否则无法区分“没有看到”和“看到了但没有关注”。

---

## 10. 策略动作采样

### 10.1 Softmax

\[
P(a_k)=
\frac{\exp((z_k-z_{\max})/T)}
{\sum_j\exp((z_j-z_{\max})/T)}
\]

要求：

- 先应用动作掩码；
- 用稳定softmax；
- `T`必须有下限；
- 无有效动作时返回显式NOOP或错误；
- 记录概率和熵。

### 10.2 Gumbel-Max

\[
a=\arg\max_k(z_k+g_k),\quad g_k\sim Gumbel(0,1)
\]

适用于类别采样和可复现并行实现。

### 10.3 温度来源

温度可以是：

- 全局配置；
- 主体类型参数；
- 遗传参数；
- 内部状态函数；
- 学习策略输出。

但温度不应隐式依赖实验分析指标。

---

## 11. 执行误差

动作被选择后，还需要执行采样：

- 移动偏差；
- 攻击命中；
- 连接建立；
- 资源转化失败；
- 繁殖成功；
- 信号发送失败。

策略采样随机流与执行随机流必须分开，以便区分“决策不确定”和“身体执行失败”。

---

## 12. 冲突随机

多个主体争夺同一目标时：

- 按能力比例；
- 按投入资源；
- 按先后；
- 按制度优先级；
- 随机；
- 混合方式。

冲突采样键应基于稳定目标事件ID，而不是任一参与者的数组索引。

参与者排序必须稳定，避免输入顺序改变概率对应关系。

---

## 13. 变异采样

变异至少区分：

- 参数小扰动；
- 模块开关；
- 模块类型改变；
- 网络调制向量变化；
- 传感器变化；
- 学习率变化；
- 社会偏好变化。

大结构变异应低频，参数变异可高频。变异结果必须记录父代、键、变异类型和变异幅度。

---

## 14. 采样审计日志

完整轨迹抽样主体应记录：

```text
SamplingAudit
{
    tick
    subject_id
    operation
    stream_id
    random_key
    distribution
    parameters
    candidate_count
    selected_value
    selected_probability
}
```

普通主体只记录聚合统计，避免日志爆炸。

---

## 15. 统计验证

每个分布实现必须通过：

- 均值和方差；
- 分位数；
- 卡方或KS检验；
- 序列相关；
- 跨stream相关；
- CPU/GPU一致性；
- 大规模并行重复；
- 极端参数测试。

采样系统变更必须触发统计回归测试。

---

## 16. 采样消融实验

至少比较：

- 完全确定性；
- 低温；
- 中温；
- 高温；
- Softmax；
- Gumbel-Max；
- 不同邻居采样；
- 无接收偏差；
- 仅传播噪声；
- 仅接收噪声；
- 仅记忆误差；
- 完整误差链。

关注指标：

- 生存和繁殖；
- 群体形成；
- 信任网络；
- 欺骗；
- 主体偏移；
- 适应速度；
- 多样性；
- 系统崩溃率。

---

## 17. API错误处理

以下情况必须显式失败：

- 概率含NaN；
- 权重全负；
- mask全部无效且无NOOP；
- 标准差为负；
- 温度小于下限；
- 重复使用不允许重复的draw_index；
- 未注册stream_id；
- 业务代码绕过统一API。

调试模式下可启用随机键碰撞检测。

---

## 18. 强化学习兼容

RL策略仍必须调用相同动作采样接口。

训练时可以记录：

- logits；
- 概率；
- entropy；
- value estimate；
- action mask；
- observation age；
- uncertainty。

环境随机与策略探索随机必须使用不同stream，以支持：

- 固定环境随机、比较策略；
- 固定策略随机、比较环境；
- 反事实重放；
- 离线训练。

---

## 19. 统一采样验收

必须达到：

- 所有业务随机均可搜索到API调用；
- 相同键产生相同结果；
- 增加无关主体不改变其他主体随机序列；
- 增加日志不改变轨迹；
- CPU/GPU基础分布统计一致；
- 邻居采样偏差被记录；
- 策略和执行随机可分离；
- 信息误差各阶段可独立关闭；
- 采样配置进入实验哈希。
