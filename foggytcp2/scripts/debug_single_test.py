#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单次传输调试脚本 - 用于诊断为什么实验失败
"""

import subprocess
import time
import signal
import re
from pathlib import Path

# 配置
FOGGY_DIR = Path("/home/serennan/work/algo2/foggytcp2/foggytcp")
TEST_FILE = Path("/home/serennan/work/algo2/foggytcp2/testdata/test_1mb.bin")
OUTPUT_FILE = Path("/home/serennan/work/algo2/foggytcp2/results/debug_output.bin")

SERVER_BIN = FOGGY_DIR / "server"
CLIENT_BIN = FOGGY_DIR / "client"
SERVER_IP = "127.0.0.1"
SERVER_PORT = 15441
TIMEOUT = 30  # 30秒超时

print("=" * 60)
print("单次传输调试测试")
print("=" * 60)
print(f"Server: {SERVER_BIN}")
print(f"Client: {CLIENT_BIN}")
print(f"Test file: {TEST_FILE} ({TEST_FILE.stat().st_size} bytes)")
print(f"Output: {OUTPUT_FILE}")
print(f"Timeout: {TIMEOUT} seconds")
print()

# 启动 server
print("[1] 启动 server...")
server_cmd = [str(SERVER_BIN), SERVER_IP, str(SERVER_PORT), str(OUTPUT_FILE)]
print(f"    命令: {' '.join(server_cmd)}")

server_proc = subprocess.Popen(
    server_cmd,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)
print(f"    Server PID: {server_proc.pid}")
time.sleep(1)  # 等待server启动

# 检查server是否还在运行
if server_proc.poll() is not None:
    print(f"    [错误] Server启动失败!")
    stdout, stderr = server_proc.communicate()
    print(f"    stdout: {stdout}")
    print(f"    stderr: {stderr}")
    exit(1)
print("    Server运行中...")

# 启动 client
print("\n[2] 启动 client...")
client_cmd = [str(CLIENT_BIN), SERVER_IP, str(SERVER_PORT), str(TEST_FILE)]
print(f"    命令: {' '.join(client_cmd)}")

try:
    client_result = subprocess.run(
        client_cmd,
        timeout=TIMEOUT,
        capture_output=True,
        text=True
    )

    print(f"    Client返回码: {client_result.returncode}")

    if client_result.returncode != 0:
        print(f"    [错误] Client异常退出")
        print(f"\n    === Client stdout ===")
        print(client_result.stdout[:500])
        print(f"\n    === Client stderr ===")
        print(client_result.stderr[:500])
    else:
        print(f"    [成功] Client正常完成")

except subprocess.TimeoutExpired:
    print(f"    [超时] Client执行超过{TIMEOUT}秒")
    server_proc.kill()
    exit(1)

# 等待server输出
print("\n[3] 获取 server 输出...")
time.sleep(0.5)

# 终止server
print("    发送SIGTERM信号...")
server_proc.send_signal(signal.SIGTERM)

try:
    stdout, stderr = server_proc.communicate(timeout=5)

    print(f"\n    === Server stdout (最后1000字符) ===")
    print(stdout[-1000:] if len(stdout) > 1000 else stdout)

    print(f"\n    === Server stderr ===")
    print(stderr[:500] if stderr else "(无)")

    # 尝试解析时间
    pattern = r"Complete transmission in (\d+) ms"
    match = re.search(pattern, stdout)

    if match:
        duration_ms = int(match.group(1))
        file_size = TEST_FILE.stat().st_size
        throughput_mbps = (file_size * 8 / (duration_ms / 1000.0)) / 1e6

        print("\n" + "=" * 60)
        print("[成功] 找到传输时间!")
        print("=" * 60)
        print(f"传输时长: {duration_ms} ms")
        print(f"文件大小: {file_size} bytes ({file_size/1e6:.2f} MB)")
        print(f"吞吐量: {throughput_mbps:.2f} Mbps")
    else:
        print("\n" + "=" * 60)
        print("[失败] 未找到 'Complete transmission in XXX ms'")
        print("=" * 60)
        print("可能原因:")
        print("1. 传输未完成")
        print("2. Server代码没有输出这行信息")
        print("3. 输出被调试信息淹没")

except subprocess.TimeoutExpired:
    print("    [超时] Server未在5秒内退出,强制kill")
    server_proc.kill()

# 检查输出文件
print("\n[4] 检查输出文件...")
if OUTPUT_FILE.exists():
    output_size = OUTPUT_FILE.stat().st_size
    input_size = TEST_FILE.stat().st_size
    print(f"    输出文件大小: {output_size} bytes")
    print(f"    输入文件大小: {input_size} bytes")
    if output_size == input_size:
        print(f"    [成功] 文件大小匹配!")
    else:
        print(f"    [警告] 文件大小不匹配 (差异: {abs(output_size - input_size)} bytes)")
else:
    print(f"    [错误] 输出文件不存在")

print("\n" + "=" * 60)
print("调试测试完成")
print("=" * 60)
