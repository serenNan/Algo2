# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是一个 TCP 拥塞控制算法研究项目（algo2），包含两个主要部分：
1. **FoggyTCP 实现**：一个基于 C++ 的自定义 TCP 协议栈实现（位于 `foggytcp2/` 子目录）
2. **性能研究报告**：验证 Dr. Matt Mathis 假设和自定义拥塞控制算法（CCA）的设计与评估

项目使用 UDP 作为底层传输协议来模拟完整的 TCP 功能，包括滑动窗口、流量控制和拥塞控制。

## 项目结构

```
algo2/
├── foggytcp2/              # FoggyTCP 实现主目录
│   ├── foggytcp/          # 核心代码目录
│   │   ├── src/           # 源代码文件
│   │   ├── inc/           # 头文件
│   │   ├── utils/         # 工具脚本（数据包捕获等）
│   │   ├── setup/         # 环境配置文件
│   │   └── Makefile       # 构建配置
│   ├── Vagrantfile        # 虚拟机测试环境配置
│   ├── submit.py          # 作业提交脚本
│   ├── CLAUDE.md          # FoggyTCP 子项目文档
│   └── README.md          # 项目说明
└── New report&algo.pdf    # 实验要求和报告规范

```

## 核心架构

### FoggyTCP 实现（foggytcp2/foggytcp/）

#### 关键源文件
- **foggy_tcp.cc/h**: TCP 套接字主接口（read/write/open/close）
- **foggy_backend.cc/h**: 后端线程核心逻辑
  - TCP 状态机
  - 超时和重传管理
  - 缓冲区管理
  - 拥塞控制算法实现
- **foggy_function.cc/h**: TCP 功能辅助函数（学生实现区域）
- **foggy_packet.cc/h**: 数据包格式定义（**不可修改**）
- **grading.h**: 测试配置变量（会被替换）

#### 多线程架构
- **主线程**：处理应用层请求（read/write/open/close）
- **后端线程**：独立运行 TCP 协议逻辑，与应用异步工作

#### 数据结构
```cpp
// 窗口管理结构
typedef struct {
  uint32_t last_byte_sent;
  uint32_t last_ack_received;
  uint32_t dup_ack_count;
  uint32_t next_seq_expected;
  uint32_t ssthresh;              // 慢启动阈值
  uint32_t advertised_window;     // 接收方通告窗口（RWND）
  uint32_t congestion_window;     // 拥塞窗口（CWND）
  reno_state_t reno_state;        // Reno 状态机
} window_t;

// 发送窗口槽位（使用 deque）
typedef struct {
  int is_sent;
  uint8_t* msg;
  int is_rtt_sample;              // RTT 采样标记
  struct timespec send_time;
  time_t timeout_interval;
} send_window_slot_t;

// 接收窗口槽位（固定大小数组）
typedef struct {
  uint8_t* msg;
  int is_used;
} receive_window_slot_t;
```

#### TCP Reno 拥塞控制状态机
```cpp
typedef enum {
  RENO_SLOW_START = 0,          // 慢启动：CWND 每 RTT 翻倍
  RENO_CONGESTION_AVOIDANCE = 1, // 拥塞避免：CWND 每 RTT 增加 1 MSS
  RENO_FAST_RECOVERY = 2,        // 快速恢复：3 个重复 ACK 触发
} reno_state_t;
```

## 常用命令

### 构建命令（在 foggytcp2/foggytcp/ 目录下执行）

```bash
# 构建 FoggyTCP 版本
cd foggytcp2/foggytcp
make foggy           # 构建服务器和客户端
make server-foggy    # 仅构建服务器
make client-foggy    # 仅构建客户端

# 构建系统 TCP 版本（用于对比测试）
make system
make server-system
make client-system

# 清理构建产物
make clean

# 代码格式化
make format
```

### 测试环境说明

**方式 1：直接在 Linux 环境测试（推荐）**
如果您已经在 Linux 环境下工作，可以直接在本地测试：

```bash
# 在一个终端启动服务器
cd foggytcp2/foggytcp
./server 15441

# 在另一个终端启动客户端（连接到本地）
cd foggytcp2/foggytcp
./client 127.0.0.1 15441
```

**方式 2：使用 Vagrant 虚拟机（可选）**
仅当需要模拟完整的网络环境（如多台机器）时使用：

```bash
cd foggytcp2

# 启动虚拟机
vagrant up

# SSH 连接到不同 VM
vagrant ssh client   # 客户端 VM (10.0.1.2)
vagrant ssh server   # 服务器 VM (10.0.1.1)
```

### 网络配置和测试

**使用 tcconfig 调整网络参数**（需要先安装）：

```bash
# 安装 tcconfig（如果未安装）
pip install tcconfig

# 获取网络接口名称
ip link show

# 设置网络参数（替换 eth0 为实际接口名）
sudo tcset eth0 --rate 10Mbps --delay 20ms --loss 0.01%

# 示例：设置不同丢包率
sudo tcset eth0 --rate 10Mbps --delay 20ms --loss 0.001%  # 0.001% 丢包
sudo tcset eth0 --rate 10Mbps --delay 20ms --loss 0.1%    # 0.1% 丢包

# 查看当前网络配置
sudo tcshow eth0

# 删除网络限制
sudo tcdel eth0 --all
```

**注意**：在本地环回接口（lo）测试时，网络参数可能不会生效。如需精确控制网络条件，建议：
1. 使用 Vagrant 虚拟机环境
2. 或使用两台物理机器
3. 或使用 Docker 容器网络

### 数据包捕获和分析

```bash
# 捕获数据包
cd foggytcp2/foggytcp
./utils/capture_packets.sh

# 或手动使用 tcpdump（需要 root 权限）
sudo tcpdump -i lo -w foggy_capture.pcap port 15441

# 使用 Wireshark 分析生成的 PCAP 文件
# 记得安装 tcp.lua 插件以正确解码 FoggyTCP 头部
```

### 提交作业

```bash
cd foggytcp2
python3 submit.py  # 生成 submit.zip
```

## 实验任务

### 任务 1：验证 Dr. Matt Mathis 假设

**理论基础**：
```
throughput = (MSS/RTT) * (C/sqrt(p))
```
其中：
- MSS = 1400 bytes
- RTT = 往返时延
- p = 丢包率
- C = 常数（需要通过实验确定）

**实验步骤**：
1. 使用 `tcconfig` 设置不同的丢包率 p
2. 传输大文件（至少几秒钟）并测量传输时间
3. 计算吞吐量 = 文件大小 / 传输时间
4. 每个丢包率重复 10 次实验
5. 绘制 1/sqrt(p) vs throughput 折线图
6. 进行线性回归并在图上显示回归线

**报告要求**：
- 计算线性回归得到的常数 C
- 计算 Pearson 相关系数
- 分析数据是否支持 Mathis 假设

### 任务 2：设计自定义拥塞控制算法（CCA）

**目标**：设计一个性能优于 TCP Reno 的拥塞控制算法

**测试环境**：
- RTT = 200ms
- 路由器缓冲区无限大
- 当缓冲区深度超过 N 时，增加额外延迟 X ms

**性能指标**：
- 传输 1MB 文件的时间（越短越好）

**报告要求**：
1. **算法提案部分**：
   - 详细描述新算法或对 Reno 的改进
   - 解释为什么新算法能提高吞吐量
2. **算法评估部分**：
   - 提供 Reno 和新算法的性能对比数据
   - 测量单连接传输 1MB 的时间

**可修改内容**：
- 可以修改任何代码（除了 `foggy_packet.h`）
- 可以在数据包扩展字段中添加自定义信息

## 测试用例

项目包含以下自动化测试：

1. **test_noloss**: 无丢包情况下可靠传输 50KB 文件
2. **test_recv_window_change**: 测试发送方对接收方通告窗口变化的响应
3. **test_retransmission_after_three_dupacks**: 测试 3 个重复 ACK 后的重传
4. **test_slow_start**: 测试慢启动阶段拥塞窗口的指数增长
5. **test_loss_response**: 测试拥塞窗口对丢包的响应
6. **test_source_structure**: 源代码结构检查

## TCP Reno 实现要点

### 1. 丢包检测和恢复
- 通过 3 个重复 ACK 检测丢包（本项目简化，不考虑超时）
- 重传丢失的数据包

### 2. 流量控制
- 根据接收方通告窗口（RWND）调整发送窗口
- 发送窗口 = min(RWND, CWND)
- 从 ACK 包头的 `advertised_window` 字段获取 RWND

### 3. 拥塞控制状态转换

**慢启动（Slow Start）**：
- 初始 CWND = 1 MSS
- 每收到一个 ACK，CWND += 1 MSS
- 效果：CWND 每个 RTT 翻倍
- 当 CWND >= SSTHRESH 时，转入拥塞避免

**拥塞避免（Congestion Avoidance）**：
- CWND += (MSS * MSS) / CWND（每收到一个 ACK）
- 效果：CWND 每个 RTT 增加约 1 MSS
- 检测到 3 个重复 ACK 时，转入快速恢复

**快速恢复（Fast Recovery）**：
- 触发条件：收到 3 个重复 ACK
- 设置 SSTHRESH = CWND / 2
- 设置 CWND = SSTHRESH + 3 * MSS
- 收到新 ACK 后，设置 CWND = SSTHRESH，转入拥塞避免

## 开发注意事项

### 关键限制
- **不可修改 foggy_packet.h**：数据包格式必须保持一致，以确保跟踪脚本正常工作
- **不要在 client.cc/server.cc 中保存协议状态**：这些文件会被替换用于测试
- **grading.h 会被替换**：需要测试不同配置参数

### 调试技巧
- 编译选项已包含 `-g -ggdb` 启用调试符号
- AddressSanitizer (`-fsanitize=address`) 已启用，检测内存问题
- 使用 Wireshark + tcp.lua 插件分析数据包流
- 使用 GDB 调试：`gdb ./server` 或 `gdb ./client`
- 在代码中添加日志输出（使用 `fprintf(stderr, ...)` 输出到标准错误）

### 代码规范
- 所有注释使用英文
- 使用 `make format` 格式化代码（使用 pre-commit）

## Python 环境

项目的 Python 脚本较简单，使用系统默认 Python 3 即可：
- `submit.py`：生成提交压缩包

对于数据分析和绘图任务，推荐使用：
```bash
# 安装数据分析库（如需要）
pip install numpy matplotlib scipy pandas
```

## 参考资源

- Dr. Matt Mathis 论文：https://dl.acm.org/doi/10.1145/263932.264023
- Wireshark 插件目录：https://www.wireshark.org/docs/wsug_html_chunked/ChPluginFolders.html
- FoggyTCP 详细文档：见 `foggytcp2/README.md` 和 `foggytcp2/CLAUDE.md`
