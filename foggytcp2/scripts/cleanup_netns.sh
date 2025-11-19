#!/bin/bash
# 网络命名空间清理脚本
# 删除 Mathis 实验创建的网络命名空间和虚拟接口

set -e

echo "========================================"
echo "清理网络命名空间环境"
echo "========================================"

# 检查是否具有 root 权限
if [ "$EUID" -ne 0 ]; then
    echo "[错误] 此脚本需要 root 权限"
    echo "请使用: sudo $0"
    exit 1
fi

# 配置参数
NS_SERVER="ns_server"
NS_CLIENT="ns_client"

echo "[清理] 删除网络命名空间..."

# 删除 server 命名空间
if ip netns list | grep -q "^$NS_SERVER"; then
    ip netns del $NS_SERVER
    echo "  ✓ 已删除: $NS_SERVER"
else
    echo "  - $NS_SERVER 不存在"
fi

# 删除 client 命名空间
if ip netns list | grep -q "^$NS_CLIENT"; then
    ip netns del $NS_CLIENT
    echo "  ✓ 已删除: $NS_CLIENT"
else
    echo "  - $NS_CLIENT 不存在"
fi

echo ""
echo "========================================"
echo "清理完成!"
echo "========================================"
echo "所有网络命名空间和虚拟接口已被删除"
echo ""
