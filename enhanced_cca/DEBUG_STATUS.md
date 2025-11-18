# 调试状态报告

## 已发现的问题

### 问题 1: Backend 线程CPU 100%
**状态**: ✅ 已修复
**修复**: 在 backend 循环中添加 `usleep(1000)`

### 问题 2: 服务器ACK无法到达客户端
**状态**: ❌ 未解决
**症状**:
- 服务器接收数据包并发送 ACK (服务器日志显示 "Sending ACK")
- 客户端没有接收到 ACK (客户端日志为空,没有 "Receive ACK")
- 客户端发送窗口填满后停止发送

**已尝试的修复**:
1. ✅ 修复服务器连接地址初始化 - 不再使用 INADDR_ANY
2. ✅ 添加 `process_receive_window` 的线程安全锁

### 问题 3: Race Condition
**状态**: ✅ 已修复
**修复**: `process_receive_window` 添加 `recv_lock` 互斥锁

## 当前诊断

从日志分析:
- 服务器接收: 996846 / 1048576 字节 (95%)
- 客户端发送后卡住
- 缺失约 51KB 数据(~37个数据包)

**可能原因**:
1. UDP数据包路由问题(服务器ACK无法返回客户端)
2. Socket绑定/连接设置问题
3. recvfrom更新conn结构的问题

## 下一步调试方向

需要添加调试输出来追踪:
1. 服务器 ACK 发送的目标地址
2. 客户端套接字绑定的本地地址
3. recvfrom 是否正确更新 sock->conn

## 已修改文件

1. `foggytcp/src/foggy_backend.cc` - 添加 usleep
2. `foggytcp/src/foggy_tcp.cc` - 修复服务器conn初始化
3. `foggytcp/src/foggy_function.cc` - 添加process_receive_window锁
