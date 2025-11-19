#!/bin/bash
# 网络命名空间设置脚本
# 用于 Mathis 假设验证实验
# 创建隔离的网络环境以支持 tcconfig 网络参数控制

set -e  # 遇到错误立即退出

echo "========================================"
echo "设置网络命名空间环境"
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
VETH_SERVER="veth_server"
VETH_CLIENT="veth_client"
IP_SERVER="10.0.1.1/24"
IP_CLIENT="10.0.1.2/24"

echo "[1/6] 清理可能存在的旧配置..."
# 删除可能存在的旧命名空间
ip netns del $NS_SERVER 2>/dev/null || true
ip netns del $NS_CLIENT 2>/dev/null || true
echo "     ✓ 清理完成"

echo "[2/6] 创建网络命名空间..."
ip netns add $NS_SERVER
ip netns add $NS_CLIENT
echo "     ✓ 命名空间已创建: $NS_SERVER, $NS_CLIENT"

echo "[3/6] 创建虚拟网络接口对..."
ip link add $VETH_SERVER type veth peer name $VETH_CLIENT
echo "     ✓ 接口对已创建: $VETH_SERVER <-> $VETH_CLIENT"

echo "[4/6] 将接口分配到命名空间..."
ip link set $VETH_SERVER netns $NS_SERVER
ip link set $VETH_CLIENT netns $NS_CLIENT
echo "     ✓ 接口已分配到各自的命名空间"

echo "[5/6] 配置 IP 地址..."
ip netns exec $NS_SERVER ip addr add $IP_SERVER dev $VETH_SERVER
ip netns exec $NS_CLIENT ip addr add $IP_CLIENT dev $VETH_CLIENT
echo "     ✓ Server: $IP_SERVER"
echo "     ✓ Client: $IP_CLIENT"

echo "[6/6] 启用网络接口..."
ip netns exec $NS_SERVER ip link set dev $VETH_SERVER up
ip netns exec $NS_CLIENT ip link set dev $VETH_CLIENT up
ip netns exec $NS_SERVER ip link set dev lo up
ip netns exec $NS_CLIENT ip link set dev lo up
echo "     ✓ 所有接口已启用"

echo ""
echo "========================================"
echo "网络命名空间设置完成!"
echo "========================================"
echo ""
echo "验证网络连通性:"
echo "  从 client 到 server:"
if ip netns exec $NS_CLIENT ping -c 2 -W 2 10.0.1.1 >/dev/null 2>&1; then
    echo "    ✓ Ping 成功 (10.0.1.1)"
else
    echo "    ✗ Ping 失败"
    exit 1
fi

echo ""
echo "查看网络配置:"
echo "  Server 命名空间:"
ip netns exec $NS_SERVER ip addr show $VETH_SERVER | grep "inet "
echo "  Client 命名空间:"
ip netns exec $NS_CLIENT ip addr show $VETH_CLIENT | grep "inet "

echo ""
echo "使用方法:"
echo "  在 server 命名空间运行命令:"
echo "    sudo ip netns exec $NS_SERVER <command>"
echo ""
echo "  在 client 命名空间运行命令:"
echo "    sudo ip netns exec $NS_CLIENT <command>"
echo ""
echo "  设置网络参数 (在 client 端):"
echo "    sudo ip netns exec $NS_CLIENT tcset $VETH_CLIENT --rate 10Mbps --delay 20ms --loss 0.01%"
echo ""
echo "清理环境请运行: sudo ./cleanup_netns.sh"
echo "========================================"
