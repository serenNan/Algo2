# Dr. Matt Mathis 假设验证实验计划

## 一、实验目标

验证 TCP Reno 吞吐量方程:

**throughput = (MSS/RTT) × (C/√p)**

其中:
- **MSS** ≈ 1360 字节 (1400 - 头部大小)
- **RTT** = 往返时延 (通过 tcconfig 设置)
- **p** = 丢包概率
- **C** = 常数 (需通过线性回归确定)

**验证目标**:
1. 通过线性回归求出常数 C 的值
2. 计算 1/√p 与实测吞吐量之间的皮尔逊相关系数
3. 判断实验数据是否支持 Mathis 假设

---

## 二、实验环境

### 2.1 项目信息
- **项目路径**: `/home/serennan/work/algo2/foggytcp2/foggytcp`
- **发送端**: `client` (读取文件并通过 FoggyTCP 发送)
- **接收端**: `server` (接收文件并输出传输时间)
- **协议实现**: TCP Reno with Fast Retransmit

### 2.2 网络配置
- **工具**: tcconfig (`tcset`, `tcshow`, `tcdel`)
- **固定参数**:
  - 带宽: 10 Mbps
  - 延迟: 20 ms (单向延迟,RTT = 40 ms)
- **变量参数**:
  - 丢包率 p: 多个不同值

### 2.3 测试文件
建议文件大小: **1MB - 10MB**
- 确保传输时间 ≥ 3 秒
- 避免过短导致测量误差
- 文件存放位置: `foggytcp2/testdata/`

---

## 三、实验设计

### 3.1 丢包率选择

建议测试以下丢包率值:

| 序号 | 丢包率 p | 1/√p | 说明 |
|-----|---------|------|------|
| 1 | 0.01% (0.0001) | 100 | 极低丢包 |
| 2 | 0.05% (0.0005) | 44.72 | 低丢包 |
| 3 | 0.1% (0.001) | 31.62 | 中低丢包 |
| 4 | 0.5% (0.005) | 14.14 | 中等丢包 |
| 5 | 1% (0.01) | 10 | 中高丢包 |
| 6 | 2% (0.02) | 7.07 | 高丢包 |
| 7 | 5% (0.05) | 4.47 | 极高丢包 |

### 3.2 重复次数
- 每个丢包率: **10 次重复实验**
- 总实验次数: **7 × 10 = 70 次**

### 3.3 数据记录格式

CSV 文件格式 (`mathis_data.csv`):
```csv
loss_rate,trial,duration_ms,file_size_bytes,throughput_mbps,1_over_sqrt_p
0.0001,1,2345,1048576,3.57,100.0
0.0001,2,2398,1048576,3.50,100.0
...
```

字段说明:
- `loss_rate`: 丢包率 (小数形式)
- `trial`: 试验编号 (1-10)
- `duration_ms`: 传输时长 (毫秒)
- `file_size_bytes`: 文件大小 (字节)
- `throughput_mbps`: 吞吐量 (Mbps)
- `1_over_sqrt_p`: 1/√p 值

---

## 四、实验步骤

### 阶段 1: 环境准备 (预计 30 分钟)

#### 1.1 编译项目
```bash
cd /home/serennan/work/algo2/foggytcp2/foggytcp
make clean
make foggy
```

验证生成的可执行文件:
- `./server`
- `./client`

#### 1.2 创建目录结构
```bash
mkdir -p foggytcp2/scripts      # 实验脚本
mkdir -p foggytcp2/testdata     # 测试文件
mkdir -p foggytcp2/results      # 实验结果
```

#### 1.3 准备测试文件
```bash
# 创建 5MB 测试文件
dd if=/dev/urandom of=foggytcp2/testdata/test_5mb.bin bs=1M count=5
```

#### 1.4 安装 Python 依赖
```bash
# 使用 conda 环境
conda activate base  # 或其他合适的环境
pip install numpy scipy matplotlib pandas
```

---

### 阶段 2: 实验脚本开发 (预计 2-3 小时)

#### 2.1 实验执行脚本

**文件**: `foggytcp2/scripts/experiment_mathis.py`

**功能**:
1. 自动化配置网络参数 (tcconfig)
2. 启动 server 和 client 进程
3. 提取传输时间并计算吞吐量
4. 保存数据到 CSV 文件

**关键逻辑**:
```python
import subprocess
import time
import csv
import os
import signal

# 配置参数
LOSS_RATES = [0.0001, 0.0005, 0.001, 0.005, 0.01, 0.02, 0.05]
TRIALS_PER_LOSS = 10
BANDWIDTH = "10Mbps"
DELAY = "20ms"
INTERFACE = "eth0"  # 根据实际网络接口调整
TEST_FILE = "../testdata/test_5mb.bin"
SERVER_IP = "127.0.0.1"
SERVER_PORT = 15441

# 主循环
for loss_rate in LOSS_RATES:
    for trial in range(1, TRIALS_PER_LOSS + 1):
        # 1. 设置网络参数
        set_network_config(loss_rate)

        # 2. 启动 server (后台进程)
        server_proc = start_server()

        # 3. 启动 client 并获取输出
        duration_ms = run_client_and_get_duration()

        # 4. 计算吞吐量
        throughput = calculate_throughput(duration_ms)

        # 5. 保存数据
        save_to_csv(loss_rate, trial, duration_ms, throughput)

        # 6. 清理进程
        cleanup(server_proc)

        # 7. 短暂延迟,避免端口占用问题
        time.sleep(2)

# 清理网络配置
cleanup_network()
```

**注意事项**:
- 需要 sudo 权限执行 tcconfig 命令
- 每次实验后要清理网络限制,避免累积
- Server 输出格式: `Complete transmission in X ms`
- 异常处理: 如果传输卡住(超时重传失败),记录为失败并重试

---

#### 2.2 数据分析脚本

**文件**: `foggytcp2/scripts/analyze_mathis.py`

**功能**:
1. 加载实验数据
2. 计算统计量(均值、标准差)
3. 线性回归分析
4. 计算相关系数
5. 生成可视化图表

**分析流程**:

##### 步骤 1: 数据预处理
```python
import pandas as pd
import numpy as np

# 读取数据
df = pd.read_csv('../results/mathis_data.csv')

# 按丢包率分组,计算统计量
grouped = df.groupby('loss_rate').agg({
    'throughput_mbps': ['mean', 'std'],
    '1_over_sqrt_p': 'first'
})
```

##### 步骤 2: 线性回归
```python
from scipy import stats

# 提取 x, y 数据
x = grouped['1_over_sqrt_p'].values  # 1/√p
y = grouped['throughput_mbps']['mean'].values  # 平均吞吐量

# 线性回归
slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

# 计算常数 C
MSS = 1360  # bytes
RTT = 0.04  # 40ms = 0.04s
C = (slope * RTT) / (MSS / 1e6)  # 转换为 Mbps 单位

print(f"回归斜率: {slope:.4f}")
print(f"截距: {intercept:.4f}")
print(f"常数 C: {C:.4f}")
print(f"R²: {r_value**2:.4f}")
```

##### 步骤 3: 皮尔逊相关系数
```python
# 使用所有数据点(不仅仅是平均值)
all_x = df['1_over_sqrt_p'].values
all_y = df['throughput_mbps'].values

pearson_r, pearson_p = stats.pearsonr(all_x, all_y)
print(f"皮尔逊相关系数: {pearson_r:.4f}")
print(f"P 值: {pearson_p:.6f}")
```

##### 步骤 4: 可视化
```python
import matplotlib.pyplot as plt

plt.figure(figsize=(10, 6))

# 散点图 - 所有数据点
plt.scatter(df['1_over_sqrt_p'], df['throughput_mbps'],
            alpha=0.3, s=30, label='实验数据点')

# 平均值折线
plt.plot(grouped['1_over_sqrt_p'], grouped['throughput_mbps']['mean'],
         'o-', linewidth=2, markersize=8, label='平均吞吐量')

# 回归线
x_line = np.linspace(x.min(), x.max(), 100)
y_line = slope * x_line + intercept
plt.plot(x_line, y_line, 'r--', linewidth=2,
         label=f'回归线: y = {slope:.4f}x + {intercept:.4f}')

# 标注
plt.xlabel('1/√p', fontsize=14)
plt.ylabel('吞吐量 (Mbps)', fontsize=14)
plt.title('Dr. Matt Mathis 假设验证\nTCP Reno 吞吐量 vs 1/√p', fontsize=16)
plt.legend(fontsize=12)
plt.grid(True, alpha=0.3)

# 添加文本框显示统计信息
textstr = f'C = {C:.4f}\nR² = {r_value**2:.4f}\nPearson r = {pearson_r:.4f}'
plt.text(0.05, 0.95, textstr, transform=plt.gca().transAxes,
         fontsize=12, verticalalignment='top',
         bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

plt.tight_layout()
plt.savefig('../results/mathis_plot.png', dpi=300)
plt.show()
```

---

### 阶段 3: 执行实验 (预计 1-2 小时)

#### 3.1 运行实验脚本
```bash
cd /home/serennan/work/algo2/foggytcp2/scripts
sudo python experiment_mathis.py
```

**监控要点**:
- 观察每次传输是否成功完成
- 检查是否有卡住的情况(根据文档提示,可能因缺少超时重传而卡住)
- 记录失败的试验,必要时重新运行

#### 3.2 中间检查
每完成一组丢包率的实验后:
- 检查 CSV 文件是否正确写入
- 验证吞吐量值是否在合理范围内
- 如发现异常,及时调整

---

### 阶段 4: 数据分析与可视化 (预计 1 小时)

#### 4.1 运行分析脚本
```bash
cd /home/serennan/work/algo2/foggytcp2/scripts
python analyze_mathis.py
```

**输出内容**:
- 回归参数 (斜率、截距)
- 常数 C 的值
- R² 决定系数
- 皮尔逊相关系数及显著性
- 生成图表文件: `../results/mathis_plot.png`

#### 4.2 结果验证
- C 值理论范围: 0.5 - 2.0 (根据文献)
- R² 应该 > 0.8 表示良好拟合
- 皮尔逊 r 应该 > 0.9 表示强相关

---

### 阶段 5: 报告撰写 (预计 1-2 小时)

#### 5.1 更新实验报告

在 `/home/serennan/work/algo2/实验报告与算法.md` 中补充以下内容:

**第一部分:Dr. Matt Mathis 假设验证**

##### 5.1.1 实验设置
```markdown
### 实验设置

#### 网络参数
- 带宽: 10 Mbps
- RTT: 40 ms (单向延迟 20 ms)
- 丢包率: 0.01%, 0.05%, 0.1%, 0.5%, 1%, 2%, 5%

#### 测试配置
- 测试文件大小: 5 MB
- 每个丢包率重复: 10 次
- 总实验次数: 70 次
- MSS: 1360 字节
```

##### 5.1.2 实验数据表格
```markdown
### 实验数据

| 丢包率 p | 1/√p | 平均吞吐量 (Mbps) | 标准差 | 最小值 | 最大值 |
|---------|------|------------------|--------|--------|--------|
| 0.01%   | 100  | X.XX             | X.XX   | X.XX   | X.XX   |
| ...     | ...  | ...              | ...    | ...    | ...    |
```

##### 5.1.3 线性回归结果
```markdown
### 线性回归分析

#### 回归方程
throughput = {slope} × (1/√p) + {intercept}

#### 常数 C 的计算
根据公式 throughput = (MSS/RTT) × (C/√p)，我们有:
- 斜率 slope = (MSS/RTT) × C
- C = slope × RTT / MSS
- C = {slope} × 0.04 / (1360/1e6)
- **C = {C_value}**

#### 拟合优度
- R² (决定系数): {r_squared}
- 标准误差: {std_err}
```

##### 5.1.4 相关性分析
```markdown
### 皮尔逊相关系数

- **皮尔逊相关系数 r**: {pearson_r}
- **P 值**: {p_value}
- **显著性**: {是/否显著} (α = 0.05)

相关系数解释:
- |r| > 0.9: 强相关
- 0.7 < |r| ≤ 0.9: 中等相关
- |r| ≤ 0.7: 弱相关
```

##### 5.1.5 实验图表
```markdown
### 实验结果可视化

![Mathis 假设验证](foggytcp2/results/mathis_plot.png)

**图说明**:
- 蓝色散点: 70 次实验的原始数据点
- 橙色折线: 每个丢包率下的平均吞吐量
- 红色虚线: 线性回归拟合线
```

##### 5.1.6 结论与讨论
```markdown
### 结论

#### 假设验证结果
基于实验数据,我们得出以下结论:

1. **C 值**: 实验测得 C ≈ {C_value}
2. **相关性**: 1/√p 与吞吐量的皮尔逊相关系数为 {pearson_r}
3. **假设支持度**: {强烈支持/部分支持/不支持} Dr. Mathis 假设

#### 理由分析
- 线性拟合的 R² 值为 {r_squared}，表明 {良好/一般/较差} 的线性关系
- 相关系数 {高于/低于} 0.9，说明 {强/弱} 相关性
- 常数 C 值 {符合/不符合} 理论预期范围 (0.5-2.0)

#### 误差来源分析
可能的误差来源包括:
1. 网络环境波动(即使使用 tcconfig 仍有系统级抖动)
2. 测量精度限制(毫秒级计时)
3. 缺少超时重传导致部分实验卡住
4. 缓冲区排队延迟的影响
5. 快速恢复机制的实现细节差异

#### 改进建议
1. 增加重复次数以减少随机误差
2. 使用更长的测试文件以提高时间测量精度
3. 在更稳定的网络环境(如虚拟机网络)中测试
4. 实现超时重传以避免卡死情况
```

---

## 五、预期产出

### 5.1 代码文件
- `foggytcp2/scripts/experiment_mathis.py` - 实验执行脚本
- `foggytcp2/scripts/analyze_mathis.py` - 数据分析脚本
- `foggytcp2/testdata/test_5mb.bin` - 测试文件

### 5.2 数据文件
- `foggytcp2/results/mathis_data.csv` - 原始实验数据
- `foggytcp2/results/mathis_summary.txt` - 统计摘要

### 5.3 图表文件
- `foggytcp2/results/mathis_plot.png` - 回归分析图

### 5.4 报告文档
- `实验报告与算法.md` - 更新后的完整报告(包含第一部分)

---

## 六、时间估算

| 阶段 | 任务 | 预计时间 |
|-----|------|---------|
| 1 | 环境准备 | 30 分钟 |
| 2 | 脚本开发 | 2-3 小时 |
| 3 | 执行实验 | 1-2 小时 |
| 4 | 数据分析 | 1 小时 |
| 5 | 报告撰写 | 1-2 小时 |
| **总计** | | **6-9 小时** |

---

## 七、风险与应对

### 7.1 可能遇到的问题

#### 问题 1: 程序卡住不动
**原因**: 文档提示"由于缺少超时重传,有时程序可能卡住"

**应对**:
- 设置实验脚本超时机制(例如 60 秒)
- 超时后强制杀死进程并重试
- 记录卡住的丢包率,分析是否有规律

#### 问题 2: tcconfig 需要 sudo 权限
**应对**:
- 方案 1: 使用 sudo 运行整个 Python 脚本
- 方案 2: 配置 sudoers 允许无密码执行 tcset/tcdel
- 方案 3: 手动分步执行,每次实验前手动设置网络

#### 问题 3: 端口占用
**应对**:
- 每次实验后添加 2-3 秒延迟
- 使用 `lsof -i :15441` 检查端口状态
- 必要时使用动态端口分配

#### 问题 4: 数据点过于分散
**应对**:
- 增加重复次数(从 10 次增加到 20 次)
- 使用更长的测试文件
- 检查网络环境是否稳定

### 7.2 备用方案

如果自动化脚本开发困难,可采用**半自动化方案**:
1. 手动执行 tcset 命令
2. 手动启动 server 和 client
3. 手动记录输出时间到 Excel/CSV
4. 使用 Python 脚本仅做数据分析部分

---

## 八、技术栈总结

### 8.1 系统工具
- **tcconfig**: 网络参数模拟
- **Make**: C++ 项目编译
- **subprocess**: Python 进程管理

### 8.2 Python 库
- **numpy**: 数值计算
- **scipy**: 统计分析与回归
- **matplotlib**: 数据可视化
- **pandas**: 数据处理
- **csv**: CSV 文件读写

### 8.3 开发环境
- Python 3.x (建议 3.8+)
- Conda 虚拟环境
- Fish Shell

---

## 九、检查清单

实验开始前确认:
- [ ] FoggyTCP 项目编译成功
- [ ] tcconfig 已安装并可正常使用
- [ ] Python 依赖已安装
- [ ] 测试文件已准备
- [ ] 目录结构已创建
- [ ] 具有 sudo 权限

实验进行中:
- [ ] 每个丢包率完成 10 次重复
- [ ] CSV 数据实时保存
- [ ] 监控异常情况并记录
- [ ] 定期检查数据合理性

实验完成后:
- [ ] 数据完整性检查(70 条记录)
- [ ] 回归分析成功执行
- [ ] 图表生成清晰可读
- [ ] 报告内容完整
- [ ] 结论有理有据

---

## 十、参考文献

1. Mathis, M., Semke, J., Mahdavi, J., & Ott, T. (1997). *The macroscopic behavior of the TCP congestion avoidance algorithm*. ACM SIGCOMM Computer Communication Review, 27(3), 67-82.
   - 链接: https://dl.acm.org/doi/10.1145/263932.264023

2. TCP Reno 拥塞控制算法详解
3. tcconfig 使用文档: https://github.com/thombashi/tcconfig

---

**文档版本**: v1.0
**创建日期**: 2025-11-18
**最后更新**: 2025-11-18
