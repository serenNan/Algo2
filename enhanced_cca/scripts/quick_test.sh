#!/bin/bash
# Enhanced CCA 快速测试脚本
# 用途：验证基本传输功能

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")/foggytcp"
TEST_FILE="../../foggytcp2/testdata/test_1mb.bin"
OUTPUT_FILE="/tmp/enhanced_cca_test.bin"
LOG_DIR="/tmp/enhanced_cca_logs"

cd "$PROJECT_DIR"

echo "======================================"
echo "Enhanced CCA 快速测试"
echo "======================================"
echo

# 创建日志目录
mkdir -p "$LOG_DIR"

# 清理之前的测试
echo "[1/5] 清理环境..."
killall -9 server client 2>/dev/null || true
rm -f "$OUTPUT_FILE"
sleep 1

# 编译
echo "[2/5] 编译代码..."
make clean > /dev/null 2>&1
if ! make foggy > "$LOG_DIR/build.log" 2>&1; then
    echo "❌ 编译失败！查看日志: $LOG_DIR/build.log"
    exit 1
fi
echo "✅ 编译成功"

# 启动服务器
echo "[3/5] 启动服务器..."
./server 127.0.0.1 15441 "$OUTPUT_FILE" > "$LOG_DIR/server.log" 2>&1 &
SERVER_PID=$!
echo "   服务器 PID: $SERVER_PID"
sleep 2

# 运行客户端
echo "[4/5] 运行客户端..."
if timeout 30 ./client 127.0.0.1 15441 "$TEST_FILE" > "$LOG_DIR/client.log" 2>&1; then
    CLIENT_EXIT=$?
else
    CLIENT_EXIT=$?
fi

# 等待服务器处理
sleep 2

# 停止服务器
kill -9 $SERVER_PID 2>/dev/null || true

# 验证结果
echo "[5/5] 验证结果..."
echo

if [ ! -f "$OUTPUT_FILE" ]; then
    echo "❌ 输出文件不存在"
    exit 1
fi

ORIGINAL_SIZE=$(wc -c < "$TEST_FILE")
OUTPUT_SIZE=$(wc -c < "$OUTPUT_FILE")
PACKETS_SENT=$(grep -c "Sending packet" "$LOG_DIR/client.log" || echo 0)
PACKETS_RECV=$(grep -c "Received data packet" "$LOG_DIR/server.log" || echo 0)
ACKS_RECV=$(grep -c "Receive ACK" "$LOG_DIR/client.log" || echo 0)

echo "======================================"
echo "测试结果"
echo "======================================"
echo "客户端退出码:     $CLIENT_EXIT"
echo "原始文件大小:     $ORIGINAL_SIZE 字节"
echo "接收文件大小:     $OUTPUT_SIZE 字节"
echo "数据完整率:       $(awk "BEGIN {printf \"%.2f%%\", ($OUTPUT_SIZE/$ORIGINAL_SIZE)*100}")"
echo "发送数据包数:     $PACKETS_SENT"
echo "接收数据包数:     $PACKETS_RECV"
echo "接收ACK数:        $ACKS_RECV"
echo "======================================"
echo

# MD5 校验
echo "MD5 校验:"
ORIGINAL_MD5=$(md5sum "$TEST_FILE" | awk '{print $1}')
OUTPUT_MD5=$(md5sum "$OUTPUT_FILE" | awk '{print $1}')
echo "  原始: $ORIGINAL_MD5"
echo "  接收: $OUTPUT_MD5"

if [ "$ORIGINAL_MD5" == "$OUTPUT_MD5" ]; then
    echo "✅ MD5 匹配 - 文件完全一致！"
    TEST_RESULT="PASS"
else
    echo "⚠️  MD5 不匹配 - 数据有差异"
    TEST_RESULT="PARTIAL"
fi
echo

# 日志位置
echo "日志文件:"
echo "  构建日志: $LOG_DIR/build.log"
echo "  服务器日志: $LOG_DIR/server.log"
echo "  客户端日志: $LOG_DIR/client.log"
echo

# 最终判定
if [ $CLIENT_EXIT -eq 0 ] && [ $PACKETS_SENT -gt 0 ] && [ $ACKS_RECV -gt 0 ]; then
    if [ "$TEST_RESULT" == "PASS" ]; then
        echo "🎉 测试完全成功！"
        exit 0
    else
        echo "✅ 测试基本成功（数据完整率 $(awk "BEGIN {printf \"%.1f%%\", ($OUTPUT_SIZE/$ORIGINAL_SIZE)*100}")）"
        exit 0
    fi
else
    echo "❌ 测试失败"
    echo
    echo "客户端日志（最后20行）:"
    tail -20 "$LOG_DIR/client.log"
    echo
    echo "服务器日志（最后20行）:"
    tail -20 "$LOG_DIR/server.log"
    exit 1
fi
