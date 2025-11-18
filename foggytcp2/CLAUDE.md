# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是 ELEC3120 计算机网络课程项目 - FoggyTCP，一个自己实现的 TCP 协议栈。项目使用 C++ 开发，通过 UDP 作为底层传输协议来模拟 TCP 的各项功能。

## 架构与核心组件

### 核心文件结构
- **foggy_tcp.cc/h**: TCP 套接字主接口，处理读写、打开和关闭操作
- **foggy_backend.cc/h**: 后端线程运行的核心逻辑，处理 TCP 状态机、超时、重传、缓冲、拥塞控制等
- **foggy_packet.cc/h**: 数据包格式定义和辅助函数（不可修改）
- **foggy_function.cc/h**: TCP 功能实现的辅助函数
- **grading.h**: 测试配置变量（会被替换用于测试）

### TCP 实现要点
- 使用 UDP 作为底层协议（所有通信通过 UDP 套接字）
- 多线程架构：主线程处理应用请求，后端线程处理 TCP 逻辑
- 滑动窗口机制：发送窗口使用 deque，接收窗口使用固定大小数组
- Reno 拥塞控制：包含慢启动、拥塞避免、快速恢复三个状态

### 数据包格式（不可修改）
```
Course Number         [4 bytes]
Source Port          [2 bytes]
Destination Port     [2 bytes]
Sequence Number      [4 bytes]
Acknowledgement Number [4 bytes]
Header Length        [2 bytes]
Packet Length        [2 bytes]
Flags               [1 byte]
Advertised Window    [2 bytes]
Extension length     [2 bytes]
Extension Data      [variable]
```

## 常用构建命令

```bash
# 构建 FoggyTCP 版本
cd foggytcp
make foggy           # 构建服务器和客户端
make server-foggy    # 仅构建服务器
make client-foggy    # 仅构建客户端

# 构建系统 TCP 版本（用于对比测试）
make system          # 构建系统版本
make server-system   # 仅构建系统服务器
make client-system   # 仅构建系统客户端

# 清理构建
make clean

# 代码格式化
make format
```

## 测试环境

### Vagrant 虚拟机设置
```bash
# 启动虚拟机
vagrant up

# SSH 连接
vagrant ssh client   # 连接客户端虚拟机 (10.0.1.2)
vagrant ssh server   # 连接服务器虚拟机 (10.0.1.1)

# 网络配置
# - 速率: 100Mbps
# - 延迟: 20ms
# - 内部网络名: 3120
```

### 运行测试
```bash
# 在服务器端 (10.0.1.1)
./server <port>

# 在客户端 (10.0.1.2)
./client <server_ip> <port>
```

### 数据包捕获与分析
```bash
# 捕获数据包
./utils/capture_packets.sh

# Wireshark 分析
# 将 tcp.lua 插件复制到 Wireshark 插件目录以解码 FoggyTCP 头部
```

## 项目实现要求

### 第一部分：基础 TCP 实现
实现基本的 TCP 功能，包括：
- **序列号和确认号机制**
- **滑动窗口协议**

### 第二部分：TCP Reno 实现
需要实现以下功能：
- **丢包恢复（Loss Recovery）**
  - 通过超时检测丢包（本项目简化，不考虑超时）
  - 通过三个重复 ACK 检测丢包
  - 重传丢失的数据包

- **流量控制（Flow Control）**
  - 根据接收方的通告窗口（RWND）调整发送窗口
  - 从 ACK 包头提取 advertised_window 值
  - 发送窗口 = min(RWND, CWND)
  - 代码中使用 `window.advertised_window` 表示通告窗口大小
  - 提供 `get_advertised_window/set_advertised_window` 函数

- **拥塞控制（Congestion Control）**
  - 实现 TCP Reno 的三个状态：
    1. **慢启动（Slow Start）**：
       - 初始 CWND = 1 MSS
       - 每收到一个 ACK，CWND 增加 1 MSS
       - CWND 每个 RTT 翻倍
    2. **拥塞避免（Congestion Avoidance）**：
       - 当 CWND 达到 SSTHRESH（默认 64 MSS）
       - CWND 增加 (MSS/CWND) MSS
       - 相当于每个 RTT 增加 1 MSS
    3. **快速恢复（Fast Recovery）**：
       - 检测到三个重复 ACK 时触发
       - 设置 SSTHRESH = CWND/2
       - 设置 CWND = SSTHRESH + 3*MSS

### 状态机实现
需要实现拥塞控制的有限状态机（FSM），相关变量：
- FSM 状态：`window.reno_state`
  ```cpp
  typedef enum {
    RENO_SLOW_START = 0,
    RENO_CONGESTION_AVOIDANCE = 1,
    RENO_FAST_RECOVERY = 2,
  } reno_state_t;
  ```
- SSTHRESH：`window.ssthresh`
- 初始值：`WINDOW_INITIAL_SSTHRESH`

### 测试要求
项目包含以下测试用例：
1. **test_noloss**：无丢包情况下可靠传输 50KB 文件
2. **test_recv_window_change**：测试发送方对接收方通告窗口变化的响应
3. **test_retransmission_after_three_dupacks**：测试 3 个重复 ACK 后的重传
4. **test_slow_start**：测试慢启动阶段拥塞窗口的指数增长
5. **test_loss_response**：测试拥塞窗口对丢包的响应

## 开发重点

### Checkpoint 进度
1. **Checkpoint 1**: 基础环境设置和简单数据传输
2. **Checkpoint 2**: 序列号/确认号、滑动窗口实现
3. **Checkpoint 3**: 快速重传、拥塞控制
4. **Checkpoint 4**: 高级拥塞控制算法设计与评估

### 关键实现区域
- `foggy_backend.cc`: TCP 状态机、超时管理、重传逻辑
- `window_t` 结构体: 滑动窗口和拥塞控制状态
- `send_window_slot_t`: 发送窗口槽位，包含 RTT 采样和超时信息
- `receive_window_slot_t`: 接收窗口槽位，用于缓存乱序数据包

### 测试注意事项
- `grading.h` 中的变量会被替换，需要测试不同配置
- 不要在 `client.cc` 和 `server.cc` 中保存协议相关变量
- 保持 `foggy_packet.h` 不变以确保数据包跟踪脚本正常工作

## 调试技巧
- 使用 `-g -ggdb` 编译选项启用调试信息
- 使用 AddressSanitizer (`-fsanitize=address`) 检测内存问题
- 通过 Wireshark 和 tcp.lua 插件分析数据包流
- 检查 `/vagrant/foggytcp` 中的同步代码（Vagrant 共享文件夹）
- 注释使用英文