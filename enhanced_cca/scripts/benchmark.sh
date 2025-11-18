#!/bin/bash

# TCP 性能对比测试脚本
# 使用方法: ./benchmark.sh [reno|cubic] [测试次数]

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 参数
ALGO=${1:-cubic}  # reno 或 cubic
RUNS=${2:-10}     # 测试次数

# 路径设置
if [ "$ALGO" = "reno" ]; then
    BASE_DIR="/home/serennan/work/algo2/foggytcp2/foggytcp"
    ALGO_NAME="TCP Reno"
else
    BASE_DIR="/home/serennan/work/algo2/enhanced_cca/foggytcp"
    ALGO_NAME="TCP Cubic"
fi

TEST_FILE="$BASE_DIR/../testdata/test_1mb.bin"
OUTPUT_FILE="/tmp/benchmark_output.bin"
RESULTS_FILE="/tmp/benchmark_${ALGO}_results.txt"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   $ALGO_NAME 性能测试${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 检查测试文件
if [ ! -f "$TEST_FILE" ]; then
    echo -e "${RED}错误: 测试文件不存在: $TEST_FILE${NC}"
    exit 1
fi

FILE_SIZE=$(stat -L -c%s "$TEST_FILE")
echo "测试文件: $TEST_FILE"
echo "文件大小: $FILE_SIZE 字节 ($(echo "scale=2; $FILE_SIZE/1024/1024" | bc) MB)"
echo "测试次数: $RUNS"
echo ""

# 切换到目录
cd "$BASE_DIR"

# 编译
echo -e "${YELLOW}[1/3] 编译代码...${NC}"
make clean > /dev/null 2>&1
make foggy > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo -e "${RED}编译失败!${NC}"
    exit 1
fi
echo -e "${GREEN}✓ 编译成功${NC}"
echo ""

# 清空结果文件
> "$RESULTS_FILE"
echo "测试次数,传输时间(秒),吞吐量(Mbps),文件大小,成功" > "$RESULTS_FILE"

# 运行测试
echo -e "${YELLOW}[2/3] 运行 $RUNS 次测试...${NC}"
echo ""

SUCCESS_COUNT=0

for i in $(seq 1 $RUNS); do
    echo -ne "${YELLOW}测试 $i/$RUNS: ${NC}"

    # 清理输出文件
    rm -f "$OUTPUT_FILE"

    # 启动服务器(后台,不输出)
    ./server 127.0.0.1 15441 "$OUTPUT_FILE" > /dev/null 2>&1 &
    SERVER_PID=$!
    sleep 0.5

    # 运行客户端并测量时间
    START_TIME=$(date +%s.%N)
    timeout 60 ./client 127.0.0.1 15441 "$TEST_FILE" > /dev/null 2>&1
    CLIENT_EXIT=$?
    END_TIME=$(date +%s.%N)

    # 计算耗时
    ELAPSED=$(echo "$END_TIME - $START_TIME" | bc)

    # 停止服务器
    kill $SERVER_PID 2>/dev/null || true
    wait $SERVER_PID 2>/dev/null || true
    sleep 0.2

    # 检查结果
    if [ $CLIENT_EXIT -eq 0 ] && [ -f "$OUTPUT_FILE" ]; then
        RECEIVED_SIZE=$(stat -L -c%s "$OUTPUT_FILE" 2>/dev/null || echo 0)

        if [ $RECEIVED_SIZE -gt 0 ]; then
            # 计算吞吐量 (Mbps)
            THROUGHPUT=$(echo "scale=2; $FILE_SIZE * 8 / $ELAPSED / 1000000" | bc)

            echo -e "${GREEN}✓${NC} ${ELAPSED}s, ${THROUGHPUT} Mbps"
            echo "$i,$ELAPSED,$THROUGHPUT,$RECEIVED_SIZE,1" >> "$RESULTS_FILE"
            SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        else
            echo -e "${RED}✗ 失败 (文件大小为0)${NC}"
            echo "$i,0,0,0,0" >> "$RESULTS_FILE"
        fi
    else
        echo -e "${RED}✗ 失败 (超时或客户端错误)${NC}"
        echo "$i,0,0,0,0" >> "$RESULTS_FILE"
    fi

    # 清理
    killall -9 server client 2>/dev/null || true
    sleep 0.3
done

echo ""

# 计算统计
echo -e "${YELLOW}[3/3] 计算统计数据...${NC}"
echo ""

# 提取成功的测试数据
awk -F',' '$5==1 {print $2}' "$RESULTS_FILE" > /tmp/times.txt
awk -F',' '$5==1 {print $3}' "$RESULTS_FILE" > /tmp/throughput.txt

if [ -s /tmp/times.txt ]; then
    # 平均传输时间
    AVG_TIME=$(awk '{sum+=$1} END {print sum/NR}' /tmp/times.txt)

    # 平均吞吐量
    AVG_THROUGHPUT=$(awk '{sum+=$1} END {print sum/NR}' /tmp/throughput.txt)

    # 标准差 (时间)
    STDDEV_TIME=$(awk -v avg=$AVG_TIME '{sum+=($1-avg)^2} END {print sqrt(sum/NR)}' /tmp/times.txt)

    # 最小/最大时间
    MIN_TIME=$(sort -n /tmp/times.txt | head -1)
    MAX_TIME=$(sort -n /tmp/times.txt | tail -1)

    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}   测试结果统计${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "成功测试: $SUCCESS_COUNT / $RUNS"
    echo ""
    printf "平均传输时间: %.3f 秒\n" $AVG_TIME
    printf "标准差:       %.3f 秒\n" $STDDEV_TIME
    printf "最快:         %.3f 秒\n" $MIN_TIME
    printf "最慢:         %.3f 秒\n" $MAX_TIME
    echo ""
    printf "平均吞吐量:   %.2f Mbps\n" $AVG_THROUGHPUT
    echo ""
    echo -e "${GREEN}详细数据已保存到: $RESULTS_FILE${NC}"
    echo ""

    # 保存汇总
    echo "" >> "$RESULTS_FILE"
    echo "=== 统计汇总 ===" >> "$RESULTS_FILE"
    echo "成功测试: $SUCCESS_COUNT / $RUNS" >> "$RESULTS_FILE"
    echo "平均时间: $AVG_TIME 秒" >> "$RESULTS_FILE"
    echo "标准差: $STDDEV_TIME 秒" >> "$RESULTS_FILE"
    echo "平均吞吐量: $AVG_THROUGHPUT Mbps" >> "$RESULTS_FILE"
else
    echo -e "${RED}没有成功的测试数据!${NC}"
    exit 1
fi

# 清理临时文件
rm -f /tmp/times.txt /tmp/throughput.txt "$OUTPUT_FILE"

echo -e "${GREEN}测试完成!${NC}"
