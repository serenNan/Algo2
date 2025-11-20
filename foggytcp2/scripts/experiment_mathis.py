#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dr. Matt Mathis 假设验证实验脚本
自动化执行不同丢包率下的吞吐量测试
"""

import subprocess
import time
import csv
import os
import signal
import sys
import re
from pathlib import Path

# ============ 配置参数 ============
# Mathis 假设验证实验 - 使用系统 TCP (标准 TCP Reno)
# 使用网络命名空间 + Python计时方案
LOSS_RATES = [0.0001, 0.0002, 0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1]
TRIALS_PER_LOSS = 15  # 每个丢包率重复次数 (项目要求)
BANDWIDTH = "10Mbps"  # 带宽
DELAY = "50ms"  # 单向延迟 (RTT = 100ms)
TIMEOUT_SECONDS = 600  # 单次传输超时时间(秒)

# 网络命名空间配置
NS_SERVER = "ns_server"
NS_CLIENT = "ns_client"
INTERFACE = "veth_client"  # 客户端命名空间中的虚拟网卡
SERVER_IP = "10.0.1.1"  # 服务器在命名空间中的IP
CLIENT_IP = "10.0.1.2"  # 客户端在命名空间中的IP

# 文件路径配置
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
FOGGY_DIR = PROJECT_ROOT / "foggytcp"
TEST_FILE = PROJECT_ROOT / "testdata" / "test_10mb.bin"  # 使用1MB文件,传输更快
RESULTS_DIR = PROJECT_ROOT / "results"
OUTPUT_CSV = RESULTS_DIR / "mathis_data.csv"

SERVER_PORT = 15441
SERVER_BIN = FOGGY_DIR / "server"
CLIENT_BIN = FOGGY_DIR / "client"

# ============ 辅助函数 ============

def cleanup_network():
    """清理网络限制配置"""
    print(f"\n[清理] 删除网络接口 {INTERFACE} 上的所有限制...")
    try:
        subprocess.run(["sudo", "ip", "netns", "exec", NS_CLIENT,
                       "tcdel", INTERFACE, "--all"],
                      check=False, capture_output=True)
        print("[清理] 网络限制已清除")
    except Exception as e:
        print(f"[警告] 清理网络失败: {e}")


def set_network_config(loss_rate):
    """设置网络参数"""
    # 先清理之前的配置
    subprocess.run(["sudo", "ip", "netns", "exec", NS_CLIENT,
                   "tcdel", INTERFACE, "--all"],
                   check=False, capture_output=True)

    # 设置新配置
    loss_percent = loss_rate * 100  # 转换为百分比
    cmd = [
        "sudo", "ip", "netns", "exec", NS_CLIENT,
        "tcset", INTERFACE,
        "--rate", BANDWIDTH,
        "--delay", DELAY,
        "--loss", f"{loss_percent}%"
    ]

    print(f"\n[配置] 设置网络参数: 丢包率={loss_percent}%, 延迟={DELAY}, 带宽={BANDWIDTH}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"[错误] tcset 命令失败: {result.stderr}")
        return False

    # 验证配置
    verify_cmd = ["sudo", "ip", "netns", "exec", NS_CLIENT, "tcshow", INTERFACE]
    result = subprocess.run(verify_cmd, capture_output=True, text=True)
    print(f"[验证] 当前网络配置:\n{result.stdout}")

    return True


def start_server(output_file):
    """启动服务器进程"""
    # 在 server 命名空间中运行
    cmd = [
        "sudo", "ip", "netns", "exec", NS_SERVER,
        str(SERVER_BIN.absolute()), SERVER_IP, str(SERVER_PORT), str(Path(output_file).absolute())
    ]
    print(f"[服务器] 启动 (命名空间: {NS_SERVER})")
    print(f"[调试] 命令: {' '.join(cmd)}")

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,  # 不捕获输出
        stderr=subprocess.DEVNULL,  # 不捕获输出
        cwd=str(FOGGY_DIR.absolute())
    )

    time.sleep(1)  # 给服务器启动时间

    # 检查进程是否立即失败
    if proc.poll() is not None:
        print(f"[错误] 服务器启动失败! 返回码: {proc.returncode}")
        return None

    return proc


def run_client_and_get_duration(server_proc):
    """运行客户端并获取传输时长 (使用Python计时)"""
    # 在 client 命名空间中运行
    cmd = [
        "sudo", "ip", "netns", "exec", NS_CLIENT,
        str(CLIENT_BIN.absolute()), SERVER_IP, str(SERVER_PORT), str(TEST_FILE.absolute())
    ]
    print(f"[客户端] 启动 (命名空间: {NS_CLIENT})")
    print(f"[调试] 命令: {' '.join(cmd)}")

    try:
        # Python 计时开始
        start_time = time.time()

        # 运行客户端 (不捕获输出)
        client_result = subprocess.run(
            cmd,
            timeout=TIMEOUT_SECONDS,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        # Python 计时结束
        end_time = time.time()
        duration_ms = int((end_time - start_time) * 1000)

        if client_result.returncode != 0:
            print(f"[错误] 客户端退出异常,返回码: {client_result.returncode}")
            return None

        print(f"[客户端] 完成")
        print(f"[结果] 传输时长: {duration_ms} ms (Python计时)")

        # 等待服务器处理完成
        time.sleep(0.5)

        # 终止服务器进程
        server_proc.terminate()
        try:
            server_proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            server_proc.kill()

        return duration_ms

    except subprocess.TimeoutExpired:
        print(f"[错误] 传输超时 (>{TIMEOUT_SECONDS}秒)")
        server_proc.kill()
        return None
    except Exception as e:
        print(f"[错误] 执行客户端时出错: {e}")
        server_proc.kill()
        return None


def cleanup_process(proc):
    """清理进程"""
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()


def calculate_throughput(duration_ms, file_size_bytes):
    """计算吞吐量 (Mbps)"""
    if duration_ms <= 0:
        return 0

    duration_sec = duration_ms / 1000.0
    throughput_bps = (file_size_bytes * 8) / duration_sec
    throughput_mbps = throughput_bps / 1e6

    return throughput_mbps


def save_to_csv(data_row):
    """保存数据到CSV"""
    file_exists = OUTPUT_CSV.exists()

    with open(OUTPUT_CSV, 'a', newline='') as f:
        writer = csv.writer(f)

        # 如果文件不存在,写入表头
        if not file_exists:
            writer.writerow([
                'loss_rate', 'trial', 'duration_ms',
                'file_size_bytes', 'throughput_mbps', '1_over_sqrt_p'
            ])

        writer.writerow(data_row)


def check_prerequisites():
    """检查前置条件"""
    print("\n[检查] 验证前置条件...")

    # 检查网络命名空间是否存在
    result = subprocess.run(["ip", "netns", "list"], capture_output=True, text=True)
    if NS_SERVER not in result.stdout or NS_CLIENT not in result.stdout:
        print(f"[错误] 网络命名空间未创建")
        print(f"请先运行: sudo {SCRIPT_DIR}/setup_netns.sh")
        return False
    else:
        print(f"[检查] 网络命名空间已就绪: {NS_SERVER}, {NS_CLIENT}")

    # 检查可执行文件
    if not SERVER_BIN.exists():
        print(f"[错误] 服务器程序不存在: {SERVER_BIN}")
        print(f"请运行: cd {FOGGY_DIR} && make system")
        return False

    if not CLIENT_BIN.exists():
        print(f"[错误] 客户端程序不存在: {CLIENT_BIN}")
        print(f"请运行: cd {FOGGY_DIR} && make system")
        return False

    print(f"[检查] 可执行文件已就绪 (系统 TCP)")

    # 检查测试文件
    if not TEST_FILE.exists():
        print(f"[错误] 测试文件不存在: {TEST_FILE}")
        print(f"请运行: dd if=/dev/urandom of={TEST_FILE} bs=1M count=1")
        return False

    print(f"[检查] 测试文件已就绪: {TEST_FILE.stat().st_size / 1e6:.2f} MB")

    # 检查结果目录
    if not RESULTS_DIR.exists():
        try:
            RESULTS_DIR.mkdir(parents=True, exist_ok=True)
            print(f"[检查] 创建结果目录: {RESULTS_DIR}")
        except PermissionError:
            print(f"[错误] 无法创建结果目录: {RESULTS_DIR}")
            print("请手动创建目录或检查权限")
            return False

    # 检查是否可以写入结果目录
    test_file = RESULTS_DIR / ".write_test"
    try:
        test_file.touch()
        test_file.unlink()
        print(f"[检查] 结果目录可写")
    except PermissionError:
        print(f"[错误] 结果目录不可写: {RESULTS_DIR}")
        print(f"请运行: sudo chown -R $USER:$USER {RESULTS_DIR}")
        return False

    # 检查 tcconfig
    result = subprocess.run(["which", "tcset"], capture_output=True)
    if result.returncode != 0:
        print("[错误] tcconfig 未安装")
        print("请运行: pip install tcconfig")
        return False

    print("[检查] tcconfig 已安装")

    # 检查 sudo 权限
    result = subprocess.run(["sudo", "-n", "true"], capture_output=True)
    if result.returncode != 0:
        print("[警告] 需要 sudo 权限,运行时需要输入密码")

    print("[检查] ✓ 所有前置条件满足")
    return True


# ============ 主实验流程 ============

def main():
    print("=" * 60)
    print("Dr. Matt Mathis 假设验证实验")
    print("=" * 60)

    # 检查前置条件
    if not check_prerequisites():
        print("\n[失败] 前置条件检查未通过,退出")
        sys.exit(1)

    # 获取文件大小
    file_size = TEST_FILE.stat().st_size
    print(f"\n[配置] 测试文件大小: {file_size / 1e6:.2f} MB")
    print(f"[配置] 丢包率列表: {LOSS_RATES}")
    print(f"[配置] 每个丢包率重复: {TRIALS_PER_LOSS} 次")
    print(f"[配置] 总实验次数: {len(LOSS_RATES) * TRIALS_PER_LOSS} 次")
    print(f"[配置] 结果保存到: {OUTPUT_CSV}")
    print("\n开始实验...")

    # 记录统计
    total_experiments = len(LOSS_RATES) * TRIALS_PER_LOSS
    completed = 0
    failed = 0

    try:
        for loss_rate in LOSS_RATES:
            print("\n" + "=" * 60)
            # 处理丢包率为 0 的情况
            if loss_rate > 0:
                sqrt_p_inv = 1 / (loss_rate ** 0.5)
                print(f"丢包率: {loss_rate * 100}% (1/√p = {sqrt_p_inv:.2f})")
            else:
                print(f"丢包率: {loss_rate * 100}% (无丢包)")
            print("=" * 60)

            # 设置网络参数
            if not set_network_config(loss_rate):
                print(f"[跳过] 无法设置网络参数,跳过此丢包率")
                failed += TRIALS_PER_LOSS
                continue

            # 等待网络配置生效
            time.sleep(2)

            # 进行重复实验
            for trial in range(1, TRIALS_PER_LOSS + 1):
                print(f"\n--- 试验 {trial}/{TRIALS_PER_LOSS} ---")

                # 临时输出文件
                output_file = RESULTS_DIR / f"temp_output_{loss_rate}_{trial}.bin"

                # 启动服务器
                server_proc = start_server(output_file)

                # 运行客户端并获取时长
                duration_ms = run_client_and_get_duration(server_proc)

                # 清理服务器进程
                cleanup_process(server_proc)

                if duration_ms is not None:
                    # 计算吞吐量
                    throughput = calculate_throughput(duration_ms, file_size)
                    # 处理丢包率为 0 的情况
                    one_over_sqrt_p = 1 / (loss_rate ** 0.5) if loss_rate > 0 else float('inf')

                    # 保存数据
                    data_row = [
                        loss_rate,
                        trial,
                        duration_ms,
                        file_size,
                        throughput,
                        one_over_sqrt_p
                    ]
                    save_to_csv(data_row)

                    print(f"[成功] 吞吐量: {throughput:.2f} Mbps")
                    completed += 1
                else:
                    print(f"[失败] 此次实验失败")
                    failed += 1

                # 清理临时文件
                if output_file.exists():
                    output_file.unlink()

                # 短暂延迟,避免端口占用
                time.sleep(2)

                # 进度报告
                progress = (completed + failed) / total_experiments * 100
                print(f"\n[进度] {completed + failed}/{total_experiments} ({progress:.1f}%) | "
                      f"成功: {completed} | 失败: {failed}")

    except KeyboardInterrupt:
        print("\n\n[中断] 用户中止实验")

    finally:
        # 清理网络配置
        cleanup_network()

    # 最终统计
    print("\n" + "=" * 60)
    print("实验完成!")
    print("=" * 60)
    print(f"总实验次数: {total_experiments}")
    print(f"成功: {completed}")
    print(f"失败: {failed}")
    print(f"成功率: {completed / total_experiments * 100:.1f}%")
    print(f"\n结果已保存到: {OUTPUT_CSV}")
    print("\n下一步: 运行 analyze_mathis.py 进行数据分析")


if __name__ == "__main__":
    main()
