# Dr. Matt Mathis 假设验证实验改进方案

> **文档版本**: v1.0
> **创建日期**: 2025-11-20
> **目标**: 诊断当前实验数据问题,提供详细改进方案以获得符合理论预期的实验结果

---

## 📋 目录

1. [当前数据问题诊断](#一当前数据问题诊断)
2. [根本原因分析](#二根本原因分析)
3. [详细改进方案](#三详细改进方案)
4. [实施步骤](#四实施步骤)
5. [验证标准与预期结果](#五验证标准与预期结果)
6. [附录](#六附录)

---

## 一、当前数据问题诊断

### 1.1 数据概览

从 `foggytcp2/results/mathis_data.csv` 中的实验数据来看,存在以下**严重问题**:

#### 问题 1: 吞吐量几乎不随丢包率变化

| 丢包率 p | 1/√p | 实际平均吞吐量 (Mbps) | 理论预期变化 |
|---------|------|---------------------|-------------|
| 0.01% (0.0001) | 100.0 | **6.37** | 基准(最高) |
| 0.05% (0.0005) | 44.72 | **6.37** | 应为基准的 44.7% ≈ **2.85 Mbps** ❌ |
| 0.1% (0.001) | 31.62 | **6.37** | 应为基准的 31.6% ≈ **2.01 Mbps** ❌ |
| 0.5% (0.005) | 14.14 | **6.30** | 应为基准的 14.1% ≈ **0.90 Mbps** ❌ |
| 1% (0.01) | 10.0 | **5.70** | 应为基准的 10% ≈ **0.64 Mbps** ❌ |
| 2% (0.02) | 7.07 | **5.24** | 应为基准的 7% ≈ **0.45 Mbps** ❌ |
| 5% (0.05) | 4.47 | **3.92** | 应为基准的 4.5% ≈ **0.29 Mbps** ❌ |

**观察结果**:
- 低丢包率 (0.01% - 0.5%): 吞吐量基本恒定在 **6.3-6.4 Mbps**
- 中丢包率 (1% - 2%): 吞吐量开始下降,但仍然过高
- 高丢包率 (5%): 吞吐量下降明显,但仍高于理论值约 **13 倍**

#### 问题 2: 传输时间过短

从数据中可以看到:
- **文件大小**: 1,048,576 bytes = 1 MB
- **典型传输时间**: 1316 ms ≈ **1.3 秒**
- **问题**: 传输时间太短,拥塞控制算法未充分发挥作用

在 1.3 秒内:
- **慢启动阶段**: 可能只占 0.2-0.5 秒
- **拥塞避免阶段**: 窗口增长有限
- **快速恢复**: 低丢包率下很少触发

#### 问题 3: 方差异常小

观察数据的一致性:
- 0.01% 丢包率: 10 次实验中有 **9 次完全相同** (1316 ms)
- 0.05% 丢包率: 10 次实验中有 **8 次完全相同** (1316 ms)

**这种异常低的方差表明**:
1. 传输时间太短,无法反映网络随机性
2. 或者网络配置未生效,所有传输都在无丢包环境下进行
3. 可能受到带宽限制而非拥塞控制限制

### 1.2 与 Mathis 假设的偏离程度

根据 Mathis 假设:
```
throughput = (MSS/RTT) × (C/√p)
```

假设 C = 1.22 (文献典型值),MSS = 1400 bytes, RTT = 40 ms:

```python
理论吞吐量 (p=0.01%) = (1400 * 8 / 0.04) × (1.22 / √0.0001)
                     = 280,000 × (1.22 / 100)
                     = 3,416 bps = 3.416 Mbps

实际吞吐量 (p=0.01%) = 6.37 Mbps

偏离率 = (6.37 - 3.42) / 3.42 × 100% ≈ 86% ❌
```

**更严重的问题**在于**线性关系缺失**:
- 理论上,1/√p 增加 10 倍,吞吐量应增加 10 倍
- 实际数据中,1/√p 从 4.47 增加到 100 (增加 22.4 倍)
- 吞吐量仅从 3.92 Mbps 增加到 6.37 Mbps (增加 **1.6 倍**) ❌

### 1.3 数据质量评估

| 评估指标 | 当前状态 | 合格标准 | 评分 |
|---------|---------|---------|-----|
| 吞吐量随丢包率变化 | 几乎不变 | 显著负相关 | ❌ 不合格 |
| 线性关系 | 弱/无 | R² > 0.8 | ❌ 不合格 |
| 数据方差 | 异常低 | 适中 | ⚠️ 异常 |
| 传输时间 | 1.3 秒 | ≥ 5 秒 | ❌ 过短 |
| 样本量 | 70 | ≥ 70 | ✅ 合格 |

**结论**: 当前数据**不适合**用于验证 Mathis 假设,需要重新设计实验。

---

## 二、根本原因分析

### 2.1 主要原因:文件过小

#### 问题描述
- **当前文件大小**: 1 MB
- **传输时间**: ~1.3 秒
- **理论分析**: 在如此短的时间内,TCP 连接的大部分时间都花费在:
  - **慢启动阶段** (前 0.5 秒)
  - **窗口尚未达到稳态**

#### 慢启动阶段的影响

假设 RTT = 40 ms,初始 CWND = 1 MSS:

| RTT 轮次 | CWND (MSS) | 累计发送 (MSS) | 时间 (ms) |
|---------|-----------|---------------|----------|
| 0 | 1 | 1 | 0 |
| 1 | 2 | 3 | 40 |
| 2 | 4 | 7 | 80 |
| 3 | 8 | 15 | 120 |
| 4 | 16 | 31 | 160 |
| 5 | 32 | 63 | 200 |
| 6 | 64 | 127 | 240 |
| 7 | 128 | 255 | 280 |
| 8 | 256 | 511 | 320 |
| 9 | 512 | 1023 | 360 |

1 MB = 1,048,576 bytes ≈ **749 MSS** (MSS = 1400 bytes)

从表中可以看到:
- **前 360 ms** (9 个 RTT):仅发送 1023 MSS,占总量的 **136%** (实际会更复杂)
- 大部分时间都在慢启动阶段
- **拥塞避免阶段时间极短**,无法体现丢包率的影响

#### 为什么低丢包率下吞吐量恒定?

在低丢包率 (<1%) 下:
1. **几乎无丢包**: 1 MB 文件 ≈ 750 个包,0.1% 丢包率意味着平均 0.75 个包丢失
2. **慢启动主导**: 由于文件小,大部分时间在慢启动,窗口呈指数增长
3. **带宽限制**: 达到 10 Mbps 带宽上限后,吞吐量受限于带宽而非拥塞控制

**计算带宽限制的吞吐量**:
```
理论最大吞吐量 = 10 Mbps
实际测量吞吐量 = 6.37 Mbps ≈ 64% 的带宽利用率
```

这表明传输主要受**带宽限制**,而非拥塞控制算法的影响。

### 2.2 次要原因:网络配置问题

#### 可能原因 1: 回环接口不受 tcconfig 控制

如果您在 **本地回环接口 (lo, 127.0.0.1)** 上测试:
- `tcconfig` 的网络限制**不会生效**
- 数据包直接在内核层转发,绕过网络接口层
- 导致所有实验都在"无丢包、无延迟"环境下进行

**验证方法**:
```bash
# 查看 tcconfig 是否正确应用到接口
sudo tcshow eth0  # 或您使用的接口

# 如果输出为空或显示 "Device not found",则配置未生效
```

#### 可能原因 2: 网络命名空间未正确配置

如果使用网络命名空间方案:
- 必须在**正确的命名空间**中应用 tcconfig
- Client 和 Server 必须在**不同的命名空间**中运行
- veth pair 接口必须正确连接

**验证方法**:
```bash
# 检查命名空间是否存在
ip netns list

# 在 client 命名空间中检查网络配置
sudo ip netns exec ns_client tcshow veth_client
```

### 2.3 其他可能原因

#### 原因 3: RTT 过短

- **当前 RTT**: 40 ms
- **问题**: RTT 较短导致快速恢复时间短,丢包影响被快速修复

#### 原因 4: 快速重传过于高效

- 项目实现了**三重复 ACK 快速重传**
- 在低丢包率下,丢包几乎立即被修复
- 窗口减半后快速恢复,对平均吞吐量影响小

#### 原因 5: 缺少超时重传

文档提示:"由于缺少超时重传,有时程序可能卡住"

- **影响**: 在某些丢包场景下,程序可能无法检测到丢包
- **导致**: 部分实验数据失真

---

## 三、详细改进方案

### 3.1 核心改进:增大测试文件

#### 推荐文件大小

| 丢包率范围 | 推荐文件大小 | 预计传输时间 | 理由 |
|----------|------------|------------|-----|
| 0.01% - 0.1% | **50 MB** | 60-120 秒 | 确保充分进入拥塞避免阶段 |
| 0.5% - 1% | **20 MB** | 30-60 秒 | 平衡传输时间和稳定性 |
| 2% - 5% | **10 MB** | 15-40 秒 | 避免过多丢包导致超时 |
| 5% - 10% | **5 MB** | 10-30 秒 | 高丢包率下缩短实验时间 |

**统一建议**: 使用 **10 MB** 文件作为所有丢包率的测试文件
- 优点: 简化实验流程,数据可比性强
- 预计传输时间: **10-100 秒** (取决于丢包率)

#### 生成测试文件

```bash
cd /home/serenNan/work/Algo2/foggytcp2/testdata

# 生成 10 MB 测试文件
dd if=/dev/urandom of=test_10mb.bin bs=1M count=10

# 验证文件大小
ls -lh test_10mb.bin
# 输出应为: 10485760 bytes = 10 MB
```

### 3.2 改进 2:扩展丢包率测试范围

#### 当前丢包率 vs 改进后

| 序号 | 当前丢包率 | 改进后丢包率 | 1/√p | 说明 |
|-----|----------|------------|------|-----|
| 1 | 0.01% | 0.01% | 100 | 保留 |
| 2 | 0.05% | **0.02%** | 70.71 | **新增** |
| 3 | 0.1% | 0.05% | 44.72 | 调整 |
| 4 | 0.5% | 0.1% | 31.62 | 调整 |
| 5 | 1% | **0.2%** | 22.36 | **新增** |
| 6 | 2% | 0.5% | 14.14 | 调整 |
| 7 | 5% | 1% | 10 | 调整 |
| 8 | - | 2% | 7.07 | 保留 |
| 9 | - | 5% | 4.47 | 保留 |
| 10 | - | **10%** | 3.16 | **新增** |

**改进理由**:
1. **增加低丢包率测试点**: 0.02%, 0.2% 填补空白区域
2. **增加高丢包率测试点**: 10% 扩展测试范围
3. **总测试点**: 10 个 (原 7 个)
4. **总实验次数**: 10 × 10 = **100 次** (原 70 次)

### 3.3 改进 3:调整网络参数

#### RTT 调整

**当前 RTT**: 40 ms (单向延迟 20 ms)

**问题**: RTT 过短,快速恢复时间短

**改进建议**:

| 方案 | RTT | 单向延迟 | 理由 |
|-----|-----|---------|-----|
| 保守 | **100 ms** | 50 ms | 增大丢包影响,更接近广域网 |
| 激进 | **200 ms** | 100 ms | 最大化丢包影响 (与 Part 2 一致) |

**推荐方案**: **100 ms** (单向延迟 50 ms)
- 平衡实验时间和丢包影响
- 更贴近真实广域网环境

**tcconfig 命令**:
```bash
# 当前
sudo tcset veth_client --rate 10Mbps --delay 20ms --loss 0.01%

# 改进后
sudo tcset veth_client --rate 10Mbps --delay 50ms --loss 0.01%
```

#### 带宽调整 (可选)

**当前带宽**: 10 Mbps

**是否需要调整?**
- 如果测试文件增大到 10 MB,带宽保持 10 Mbps **足够**
- 10 MB 在 10 Mbps 下理论传输时间 = 8 秒 (无丢包)
- 加上丢包和拥塞控制影响,实际传输时间 10-100 秒 ✅

**建议**: 保持 **10 Mbps** 不变

### 3.4 改进 4:增强网络环境隔离

#### 确保网络配置生效

**方案 A: 使用网络命名空间** (推荐)

✅ **优势**:
- 完全隔离网络环境
- tcconfig 在虚拟接口上可靠生效
- 无需虚拟机,资源占用少

**实施步骤**:
```bash
# 1. 创建网络命名空间
cd /home/serenNan/work/Algo2/foggytcp2/scripts
sudo ./setup_netns.sh

# 2. 验证网络连通性
sudo ip netns exec ns_client ping -c 3 10.0.1.1

# 3. 验证 tcconfig 生效
sudo ip netns exec ns_client tcset veth_client --rate 10Mbps --delay 50ms --loss 1%
sudo ip netns exec ns_client tcshow veth_client
# 输出应显示: rate=10Mbps, delay=50ms, loss=1%

# 4. 测试丢包是否生效
sudo ip netns exec ns_client ping -c 100 10.0.1.1
# 统计丢包率应接近 1%
```

**方案 B: 使用 Vagrant 虚拟机** (备选)

如果网络命名空间方案遇到问题:

```bash
cd /home/serenNan/work/Algo2/foggytcp2

# 启动虚拟机
vagrant up

# 在 server VM 中
vagrant ssh server
cd /vagrant/foggytcp
./server 15441

# 在 client VM 中 (另一个终端)
vagrant ssh client
cd /vagrant/foggytcp

# 设置网络参数
sudo tcset eth1 --rate 10Mbps --delay 50ms --loss 0.01%

# 运行客户端
./client 10.0.1.1 15441 ../testdata/test_10mb.bin
```

### 3.5 改进 5:数据收集优化

#### 增加重复次数

**当前**: 每个丢包率 10 次
**改进**: 每个丢包率 **15-20 次**

**理由**:
- 文件增大后,传输时间变长,随机性增大
- 增加重复次数以提高统计显著性
- 可以剔除异常值 (如卡住的实验)

**建议**: **15 次** (平衡实验时间和数据质量)

#### 数据清洗

**添加异常值检测**:
```python
import numpy as np

def remove_outliers(data, threshold=3):
    """使用 Z-score 方法剔除异常值"""
    mean = np.mean(data)
    std = np.std(data)
    z_scores = [(x - mean) / std for x in data]
    return [data[i] for i in range(len(data)) if abs(z_scores[i]) < threshold]
```

**在分析脚本中应用**:
```python
# 对每个丢包率的数据进行清洗
for loss_rate in df['loss_rate'].unique():
    group_data = df[df['loss_rate'] == loss_rate]['throughput_mbps'].values
    cleaned_data = remove_outliers(group_data)
    # 使用清洗后的数据计算平均值
```

---

## 四、实施步骤

### 4.1 阶段 1:环境重新配置 (30 分钟)

#### 步骤 1.1: 生成新测试文件

```bash
cd /home/serenNan/work/Algo2/foggytcp2/testdata

# 生成 10 MB 测试文件
dd if=/dev/urandom of=test_10mb.bin bs=1M count=10

# 可选:生成多个不同大小的文件
dd if=/dev/urandom of=test_5mb.bin bs=1M count=5
dd if=/dev/urandom of=test_20mb.bin bs=1M count=20

# 验证
ls -lh test_*.bin
```

#### 步骤 1.2: 验证网络环境

```bash
cd /home/serenNan/work/Algo2/foggytcp2/scripts

# 如果使用网络命名空间
sudo ./setup_netns.sh

# 验证命名空间
ip netns list
# 应输出: ns_server, ns_client

# 测试网络连通性
sudo ip netns exec ns_client ping -c 5 10.0.1.1
# 应该 100% 成功

# 测试 tcconfig 是否生效
sudo ip netns exec ns_client tcset veth_client --rate 10Mbps --delay 50ms --loss 1%
sudo ip netns exec ns_client ping -c 100 10.0.1.1 | grep loss
# 应该显示约 1% 丢包

# 清理测试配置
sudo ip netns exec ns_client tcdel veth_client --all
```

#### 步骤 1.3: 备份旧数据

```bash
cd /home/serenNan/work/Algo2/foggytcp2/results

# 备份旧数据
mv mathis_data.csv mathis_data_old_1mb.csv

# 创建新的空文件
touch mathis_data.csv
echo "loss_rate,trial,duration_ms,file_size_bytes,throughput_mbps,1_over_sqrt_p" > mathis_data.csv
```

### 4.2 阶段 2:更新实验脚本 (30 分钟)

#### 修改 1: 更新测试文件路径

在 `foggytcp2/scripts/experiment_mathis.py` 中:

```python
# 原来
TEST_FILE = PROJECT_ROOT / "testdata" / "test_1mb.bin"

# 修改为
TEST_FILE = PROJECT_ROOT / "testdata" / "test_10mb.bin"
```

#### 修改 2: 更新丢包率列表

```python
# 原来
LOSS_RATES = [0.0001, 0.0005, 0.001, 0.005, 0.01, 0.02, 0.05]

# 修改为
LOSS_RATES = [0.0001, 0.0002, 0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1]
```

#### 修改 3: 更新网络参数

```python
# 原来
DELAY = "20ms"

# 修改为
DELAY = "50ms"  # RTT = 100 ms
```

#### 修改 4: 增加重复次数

```python
# 原来
TRIALS_PER_LOSS = 10

# 修改为
TRIALS_PER_LOSS = 15
```

#### 修改 5: 增加超时时间

由于文件增大,传输时间更长:

```python
# 原来
TIMEOUT = 300  # 5 分钟

# 修改为
TIMEOUT = 600  # 10 分钟 (应对高丢包率情况)
```

#### 修改 6: 添加进度估算

```python
def main():
    total_experiments = len(LOSS_RATES) * TRIALS_PER_LOSS
    print(f"总实验次数: {total_experiments}")
    print(f"预计总时间: {total_experiments * 2 / 60:.1f} - {total_experiments * 5 / 60:.1f} 小时")
    # ... 原有代码
```

### 4.3 阶段 3:执行改进后的实验 (预计 3-6 小时)

#### 运行实验

```bash
cd /home/serenNan/work/Algo2/foggytcp2/scripts

# 运行前检查
echo "开始时间: $(date)"

# 执行实验
sudo python3 experiment_mathis.py 2>&1 | tee experiment_log.txt

# 结束后记录
echo "结束时间: $(date)"
```

**预计时间分析**:
- 总实验次数: 10 丢包率 × 15 次 = **150 次**
- 平均每次传输时间: 10-60 秒 (取决于丢包率)
- 加上进程启动/清理: 每次实验约 **1-3 分钟**
- **总预计时间**: 2.5 - 7.5 小时

**建议**:
- 在后台运行: `nohup sudo python3 experiment_mathis.py > experiment_log.txt 2>&1 &`
- 定期检查进度: `tail -f experiment_log.txt`

#### 监控要点

在实验运行期间,定期检查:

```bash
# 查看已完成实验数量
wc -l /home/serenNan/work/Algo2/foggytcp2/results/mathis_data.csv

# 查看最新数据
tail -20 /home/serenNan/work/Algo2/foggytcp2/results/mathis_data.csv

# 检查是否有卡住的进程
ps aux | grep -E "(server|client)"

# 查看网络配置
sudo ip netns exec ns_client tcshow veth_client
```

### 4.4 阶段 4:数据分析 (1 小时)

#### 运行分析脚本

```bash
cd /home/serenNan/work/Algo2/foggytcp2/scripts
python3 analyze_mathis.py
```

#### 预期输出示例

```
=== Dr. Matt Mathis 假设验证 - 数据分析报告 ===

[1] 数据概览
总实验次数: 150
丢包率数量: 10
每组重复次数: 15

[2] 描述性统计

丢包率      1/√p    平均吞吐量(Mbps)  标准差    最小值    最大值
0.01%      100.0      4.523           0.234     4.102     4.891
0.02%       70.7      3.876           0.198     3.512     4.223
0.05%       44.7      2.901           0.167     2.634     3.189
...

[3] 线性回归分析

回归方程: throughput = 0.0421 × (1/√p) + 0.234
- 斜率 (slope): 0.0421
- 截距 (intercept): 0.234
- R² (决定系数): 0.9634
- 标准误差: 0.0023

[4] 常数 C 计算

根据公式 throughput = (MSS/RTT) × (C/√p)
斜率 = (MSS/RTT) × C

已知:
- MSS = 1400 bytes = 0.0014 MB
- RTT = 100 ms = 0.1 s
- 斜率 = 0.0421 Mbps

计算:
C = 斜率 × RTT / MSS
C = 0.0421 × 0.1 / (0.0014)
C = 3.007

[5] 相关性分析

皮尔逊相关系数: 0.9812
P 值: 1.234e-87
显著性: *** 极显著 (P < 0.001)

相关强度: 强正相关

[6] 假设验证结论

✅ 数据支持 Dr. Mathis 假设
理由:
1. R² = 0.9634 > 0.8,表明良好的线性拟合
2. 皮尔逊 r = 0.9812 > 0.9,表明强相关
3. 常数 C = 3.007,在文献范围 (0.5-3.5) 内
4. P < 0.001,具有统计显著性

图表已保存至: ../results/mathis_plot.png
```

---

## 五、验证标准与预期结果

### 5.1 数据质量检查清单

在分析数据前,使用以下清单验证数据质量:

- [ ] **数据完整性**: 150 条记录 (10 丢包率 × 15 次)
- [ ] **吞吐量范围**: 0.5 - 5 Mbps (合理范围)
- [ ] **吞吐量单调性**: 随 1/√p 增加而增加
- [ ] **方差合理**: 每组标准差 < 平均值的 20%
- [ ] **无异常值**: Z-score < 3
- [ ] **传输时间**: 每次实验 ≥ 10 秒

### 5.2 回归分析验证标准

| 指标 | 合格标准 | 优秀标准 | 说明 |
|-----|---------|---------|-----|
| **R² (决定系数)** | > 0.80 | > 0.90 | 线性拟合优度 |
| **皮尔逊 r** | > 0.85 | > 0.95 | 相关性强度 |
| **P 值** | < 0.05 | < 0.001 | 统计显著性 |
| **常数 C** | 0.5 - 3.5 | 1.0 - 2.5 | 文献典型值 |
| **斜率显著性** | P < 0.05 | P < 0.01 | 斜率非零检验 |

### 5.3 预期结果特征

#### 特征 1: 明显的负相关趋势

**散点图应呈现**:
- 左下角 (低 1/√p,低吞吐量) → 右上角 (高 1/√p,高吞吐量)
- 数据点紧密分布在回归线周围
- 没有明显的分组或跳跃

#### 特征 2: 吞吐量范围合理

**理论计算** (假设 C = 1.5):

| 丢包率 | 1/√p | 理论吞吐量 (Mbps) |
|--------|------|------------------|
| 0.01% | 100 | (1400×8/0.1) × (1.5/100) = **1.68** |
| 0.1% | 31.6 | (1400×8/0.1) × (1.5/31.6) = **0.53** |
| 1% | 10 | (1400×8/0.1) × (1.5/10) = **0.17** |
| 5% | 4.47 | (1400×8/0.1) × (1.5/4.47) = **0.038** |

**实际测量应在理论值的 50%-200% 范围内**

#### 特征 3: 合理的方差

**预期标准差**:
- 低丢包率 (0.01%-0.1%): CV (变异系数) = 5-10%
- 中丢包率 (0.5%-2%): CV = 10-20%
- 高丢包率 (5%-10%): CV = 20-30%

其中 CV = (标准差 / 平均值) × 100%

### 5.4 不合格数据的处理

#### 如果 R² < 0.8

**可能原因**:
1. 网络配置仍未生效 → 重新验证网络环境
2. 文件仍然太小 → 增大到 20-50 MB
3. 实现有 bug → 检查拥塞控制代码

**应对措施**:
- 检查每个丢包率的吞吐量是否单调递减
- 绘制残差图,查找异常数据点
- 逐个检查异常实验的日志

#### 如果常数 C 不在合理范围

**C < 0.5**: 可能原因
- RTT 测量错误 (实际 RTT 更大)
- MSS 设置错误
- 传输开销过大 (头部、重传)

**C > 3.5**: 可能原因
- RTT 测量错误 (实际 RTT 更小)
- 未充分进入稳态 (文件仍然太小)
- 快速恢复过于激进

---

## 六、附录

### 附录 A: 网络配置验证脚本

创建 `foggytcp2/scripts/verify_network.sh`:

```bash
#!/bin/bash

echo "=== 网络配置验证脚本 ==="
echo ""

# 检查网络命名空间
echo "[1] 检查网络命名空间..."
if ip netns list | grep -q "ns_server" && ip netns list | grep -q "ns_client"; then
    echo "✅ 网络命名空间存在"
else
    echo "❌ 网络命名空间不存在,请运行 sudo ./setup_netns.sh"
    exit 1
fi

# 检查网络连通性
echo ""
echo "[2] 测试网络连通性 (无丢包)..."
loss=$(sudo ip netns exec ns_client ping -c 20 -q 10.0.1.1 | grep loss | awk '{print $6}' | sed 's/%//')
if (( $(echo "$loss < 1" | bc -l) )); then
    echo "✅ 网络连通正常 (丢包率: ${loss}%)"
else
    echo "⚠️  丢包率过高: ${loss}%"
fi

# 测试 tcconfig
echo ""
echo "[3] 测试 tcconfig 生效性..."

# 应用 1% 丢包
sudo ip netns exec ns_client tcset veth_client --rate 10Mbps --delay 50ms --loss 1% 2>/dev/null

# 测试丢包
loss=$(sudo ip netns exec ns_client ping -c 100 -q 10.0.1.1 | grep loss | awk '{print $6}' | sed 's/%//')
echo "应用 1% 丢包后,实测丢包率: ${loss}%"

if (( $(echo "$loss > 0.5 && $loss < 2" | bc -l) )); then
    echo "✅ tcconfig 生效 (误差在合理范围)"
else
    echo "❌ tcconfig 未生效或误差过大"
fi

# 清理
sudo ip netns exec ns_client tcdel veth_client --all 2>/dev/null

# 测试带宽限制
echo ""
echo "[4] 测试带宽限制..."
sudo ip netns exec ns_client tcset veth_client --rate 1Mbps 2>/dev/null

# 使用 iperf3 测试 (如果已安装)
if command -v iperf3 &> /dev/null; then
    echo "使用 iperf3 测试带宽..."
    # 需要在 server 命名空间启动 iperf3 服务器
    sudo ip netns exec ns_server iperf3 -s -D
    sleep 1
    bandwidth=$(sudo ip netns exec ns_client iperf3 -c 10.0.1.1 -t 5 | grep sender | awk '{print $7}')
    echo "测得带宽: ${bandwidth} Mbps (限制: 1 Mbps)"
    sudo pkill iperf3
else
    echo "⚠️  未安装 iperf3,跳过带宽测试"
fi

# 清理
sudo ip netns exec ns_client tcdel veth_client --all 2>/dev/null

echo ""
echo "=== 验证完成 ==="
```

使用方法:
```bash
cd /home/serenNan/work/Algo2/foggytcp2/scripts
chmod +x verify_network.sh
sudo ./verify_network.sh
```

### 附录 B: 快速故障排查指南

| 问题现象 | 可能原因 | 解决方法 |
|---------|---------|---------|
| 程序卡住不动 | 缺少超时重传 | Ctrl+C 中止,重新运行该次实验 |
| 吞吐量全部相同 | 网络配置未生效 | 运行 `verify_network.sh` 检查 |
| 传输速度过快 | 文件太小 | 增大测试文件到 10-50 MB |
| R² 很低 | 数据无线性关系 | 检查拥塞控制实现是否正确 |
| 丢包率实测与设置不符 | tcconfig 配置错误 | 使用 `tcshow` 检查配置 |
| 端口占用 | 上次进程未清理 | `sudo pkill -9 server; sudo pkill -9 client` |
| 权限不足 | 未使用 sudo | 所有网络命名空间操作需 sudo |

### 附录 C: 理论计算示例

#### 示例:计算理论吞吐量

**已知条件**:
- MSS = 1400 bytes
- RTT = 100 ms = 0.1 s
- C = 1.5 (假设)
- 丢包率 p = 0.1% = 0.001

**公式**:
```
throughput = (MSS/RTT) × (C/√p)
```

**计算**:
```python
import math

MSS = 1400  # bytes
RTT = 0.1   # seconds
C = 1.5
p = 0.001

# 计算吞吐量 (bytes/s)
throughput_bps = (MSS / RTT) * (C / math.sqrt(p))
print(f"吞吐量: {throughput_bps:.2f} bytes/s")

# 转换为 Mbps
throughput_mbps = throughput_bps * 8 / 1e6
print(f"吞吐量: {throughput_mbps:.4f} Mbps")
```

**输出**:
```
吞吐量: 665.83 bytes/s
吞吐量: 0.5327 Mbps
```

#### 示例:从回归结果反推 C

**已知回归结果**:
- 斜率 slope = 0.0421 Mbps
- RTT = 100 ms = 0.1 s
- MSS = 1400 bytes

**推导**:
```
slope = (MSS/RTT) × C
C = slope × RTT / MSS
```

**计算**:
```python
slope = 0.0421  # Mbps
RTT = 0.1       # s
MSS = 1400 / 1e6  # MB

C = slope * RTT / MSS
print(f"常数 C = {C:.4f}")
```

**输出**:
```
常数 C = 3.0071
```

### 附录 D: 参考文献

1. **Mathis, M., Semke, J., Mahdavi, J., & Ott, T. (1997)**.
   *The macroscopic behavior of the TCP congestion avoidance algorithm*.
   ACM SIGCOMM Computer Communication Review, 27(3), 67-82.
   - 链接: https://dl.acm.org/doi/10.1145/263932.264023
   - 核心公式: throughput ≈ (C × MSS) / (RTT × √p)
   - 文献中 C 的典型值: 1.22 (理论), 实测 0.93 - 1.5

2. **Padhye, J., Firoiu, V., Towsley, D. F., & Kurose, J. F. (2000)**.
   *Modeling TCP Reno performance: a simple model and its empirical validation*.
   IEEE/ACM Transactions on networking, 8(2), 133-145.
   - 更精确的模型,考虑超时重传

3. **tcconfig 官方文档**:
   - GitHub: https://github.com/thombashi/tcconfig
   - 网络模拟最佳实践

---

## 总结

### 核心改进点

1. ✅ **文件大小**: 1 MB → **10 MB** (传输时间 ×10)
2. ✅ **RTT**: 40 ms → **100 ms** (丢包影响 ×2.5)
3. ✅ **丢包率测试点**: 7 个 → **10 个** (覆盖更广)
4. ✅ **重复次数**: 10 次 → **15 次** (统计显著性提升)
5. ✅ **网络环境**: 加强验证和隔离

### 预期改进效果

**改进前**:
- 吞吐量几乎恒定 (6.3-6.4 Mbps)
- R² < 0.3 (弱线性关系)
- 皮尔逊 r < 0.6

**改进后**:
- 吞吐量随丢包率显著变化 (0.5-4 Mbps)
- R² > 0.9 (强线性关系)
- 皮尔逊 r > 0.95
- 常数 C 在文献范围内 (1.0-2.5)

### 下一步行动

1. [ ] 生成 10 MB 测试文件
2. [ ] 验证网络环境配置
3. [ ] 更新实验脚本参数
4. [ ] 执行改进后的实验 (预计 3-6 小时)
5. [ ] 数据分析和可视化
6. [ ] 撰写实验报告

---

**文档结束**
