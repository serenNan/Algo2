#!/usr/bin/env python3
"""
自动化性能测试脚本
用途：对比 TCP Reno (foggytcp2) 和 Enhanced Cubic (enhanced_cca) 的性能
"""

import subprocess
import time
import os
import csv
import statistics
from pathlib import Path
from datetime import datetime

# 配置
FOGGYTCP2_DIR = "/home/serennan/work/algo2/foggytcp2/foggytcp"
ENHANCED_CCA_DIR = "/home/serennan/work/algo2/enhanced_cca/foggytcp"
TEST_FILE = "/home/serennan/work/algo2/foggytcp2/testdata/test_1mb.bin"
OUTPUT_DIR = "/home/serennan/work/algo2/results"
SERVER_IP = "127.0.0.1"
SERVER_PORT = 15441

# 测试场景
TEST_SCENARIOS = [
    {
        "name": "ideal",
        "description": "理想网络 (无延迟，无丢包)",
        "rtt_ms": 0,  # 本地回环
        "bandwidth": "1000Mbps",
        "loss_rate": 0.0,
    },
    {
        "name": "medium_rtt",
        "description": "中等延迟 (200ms RTT)",
        "rtt_ms": 100,  # 单向延迟，RTT=200ms
        "bandwidth": "10Mbps",
        "loss_rate": 0.0,
    },
    {
        "name": "with_loss",
        "description": "有损网络 (40ms RTT, 0.1% 丢包)",
        "rtt_ms": 20,
        "bandwidth": "10Mbps",
        "loss_rate": 0.001,  # 0.1%
    },
    {
        "name": "realistic",
        "description": "真实场景 (200ms RTT, 0.1% 丢包)",
        "rtt_ms": 100,
        "bandwidth": "10Mbps",
        "loss_rate": 0.001,
    },
]

TRIALS_PER_SCENARIO = 10  # 每个场景重复次数

class TestRunner:
    def __init__(self):
        self.results = []
        Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    def compile_implementation(self, impl_dir, impl_name):
        """编译实现"""
        print(f"\n{'='*60}")
        print(f"编译 {impl_name}...")
        print(f"{'='*60}")

        os.chdir(impl_dir)

        # 清理
        subprocess.run(["make", "clean"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # 编译
        result = subprocess.run(["make", "foggy"], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ 编译失败:")
            print(result.stderr)
            return False

        print(f"✅ {impl_name} 编译成功")
        return True

    def setup_network(self, scenario):
        """配置网络参数（使用 tcconfig）"""
        if scenario["rtt_ms"] == 0 and scenario["loss_rate"] == 0.0:
            # 理想网络，不需要配置
            return True

        print(f"\n配置网络: RTT={scenario['rtt_ms']*2}ms, 带宽={scenario['bandwidth']}, 丢包={scenario['loss_rate']*100}%")

        # 注意：tcconfig 需要 root 权限，在本地回环上可能不生效
        # 这里只是示例，实际可能需要使用虚拟机或真实网络

        # 获取网络接口
        try:
            # 清除之前的配置
            subprocess.run(["sudo", "tcdel", "lo", "--all"],
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)

            if scenario["rtt_ms"] > 0 or scenario["loss_rate"] > 0:
                cmd = ["sudo", "tcset", "lo"]

                if scenario["rtt_ms"] > 0:
                    cmd.extend(["--delay", f"{scenario['rtt_ms']}ms"])

                cmd.extend(["--rate", scenario["bandwidth"]])

                if scenario["loss_rate"] > 0:
                    cmd.extend(["--loss", f"{scenario['loss_rate']*100}%"])

                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    print(f"⚠️  网络配置可能失败（需要 root 权限或虚拟机环境）")
                    print(f"   继续使用本地回环测试...")
                    return True

            print("✅ 网络配置成功")
            return True

        except Exception as e:
            print(f"⚠️  网络配置跳过: {e}")
            print("   在本地回环上测试...")
            return True

    def cleanup_network(self):
        """清理网络配置"""
        try:
            subprocess.run(["sudo", "tcdel", "lo", "--all"],
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
        except:
            pass

    def run_single_test(self, impl_dir, impl_name, scenario, trial):
        """运行单次测试"""
        os.chdir(impl_dir)

        output_file = f"/tmp/test_output_{impl_name}_{scenario['name']}_{trial}.bin"

        # 清理之前的输出
        if os.path.exists(output_file):
            os.remove(output_file)

        # 启动服务器
        server_log = f"/tmp/server_{impl_name}_{scenario['name']}_{trial}.log"
        server_proc = subprocess.Popen(
            ["./server", SERVER_IP, str(SERVER_PORT), output_file],
            stdout=open(server_log, "w"),
            stderr=subprocess.STDOUT
        )

        # 等待服务器启动
        time.sleep(1)

        # 运行客户端并计时
        start_time = time.time()

        client_log = f"/tmp/client_{impl_name}_{scenario['name']}_{trial}.log"
        client_result = subprocess.run(
            ["timeout", "60", "./client", SERVER_IP, str(SERVER_PORT), TEST_FILE],
            stdout=open(client_log, "w"),
            stderr=subprocess.STDOUT,
            timeout=65
        )

        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000

        # 停止服务器
        server_proc.terminate()
        try:
            server_proc.wait(timeout=2)
        except:
            server_proc.kill()

        # 检查结果
        if client_result.returncode == 0 and os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            original_size = os.path.getsize(TEST_FILE)

            # 计算吞吐量 (Mbps)
            throughput_mbps = (file_size * 8) / (duration_ms * 1000)

            # 检查完整性
            success = file_size == original_size

            return {
                "success": success,
                "duration_ms": duration_ms,
                "throughput_mbps": throughput_mbps,
                "file_size": file_size,
                "original_size": original_size,
                "completion_rate": file_size / original_size * 100,
            }
        else:
            return {
                "success": False,
                "duration_ms": None,
                "throughput_mbps": None,
                "file_size": 0,
                "original_size": os.path.getsize(TEST_FILE),
                "completion_rate": 0,
            }

    def test_implementation(self, impl_dir, impl_name):
        """测试一个实现的所有场景"""
        print(f"\n{'='*60}")
        print(f"测试 {impl_name}")
        print(f"{'='*60}")

        for scenario in TEST_SCENARIOS:
            print(f"\n场景: {scenario['description']}")
            print(f"-" * 60)

            # 配置网络
            self.setup_network(scenario)

            scenario_results = []

            for trial in range(1, TRIALS_PER_SCENARIO + 1):
                print(f"  试验 {trial}/{TRIALS_PER_SCENARIO}...", end=" ", flush=True)

                try:
                    result = self.run_single_test(impl_dir, impl_name, scenario, trial)

                    if result["success"]:
                        print(f"✅ {result['duration_ms']:.0f}ms ({result['throughput_mbps']:.2f} Mbps)")
                    else:
                        print(f"❌ 失败 (完成率: {result['completion_rate']:.1f}%)")

                    # 记录结果
                    self.results.append({
                        "implementation": impl_name,
                        "scenario": scenario["name"],
                        "scenario_desc": scenario["description"],
                        "trial": trial,
                        "rtt_ms": scenario["rtt_ms"] * 2,
                        "bandwidth": scenario["bandwidth"],
                        "loss_rate": scenario["loss_rate"],
                        "success": result["success"],
                        "duration_ms": result["duration_ms"],
                        "throughput_mbps": result["throughput_mbps"],
                        "completion_rate": result["completion_rate"],
                    })

                    if result["success"]:
                        scenario_results.append(result)

                except Exception as e:
                    print(f"❌ 错误: {e}")

                # 短暂延迟
                time.sleep(0.5)

            # 打印场景统计
            if scenario_results:
                durations = [r["duration_ms"] for r in scenario_results]
                throughputs = [r["throughput_mbps"] for r in scenario_results]

                print(f"\n  统计:")
                print(f"    成功次数: {len(scenario_results)}/{TRIALS_PER_SCENARIO}")
                print(f"    平均时间: {statistics.mean(durations):.0f} ms (±{statistics.stdev(durations) if len(durations) > 1 else 0:.0f})")
                print(f"    平均吞吐量: {statistics.mean(throughputs):.2f} Mbps")

            # 清理网络配置
            self.cleanup_network()

    def save_results(self):
        """保存结果到 CSV"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_file = os.path.join(OUTPUT_DIR, f"benchmark_results_{timestamp}.csv")

        with open(csv_file, "w", newline="") as f:
            if self.results:
                writer = csv.DictWriter(f, fieldnames=self.results[0].keys())
                writer.writeheader()
                writer.writerows(self.results)

        print(f"\n{'='*60}")
        print(f"结果已保存到: {csv_file}")
        print(f"{'='*60}")

        return csv_file

    def print_summary(self):
        """打印测试摘要"""
        print(f"\n{'='*60}")
        print("测试摘要")
        print(f"{'='*60}\n")

        # 按实现和场景分组
        implementations = set(r["implementation"] for r in self.results)
        scenarios = set(r["scenario"] for r in self.results)

        for scenario in scenarios:
            scenario_desc = next(r["scenario_desc"] for r in self.results if r["scenario"] == scenario)
            print(f"\n场景: {scenario_desc}")
            print("-" * 60)

            for impl in implementations:
                impl_results = [
                    r for r in self.results
                    if r["implementation"] == impl and r["scenario"] == scenario and r["success"]
                ]

                if impl_results:
                    durations = [r["duration_ms"] for r in impl_results]
                    throughputs = [r["throughput_mbps"] for r in impl_results]

                    print(f"{impl:20s}: {statistics.mean(durations):7.0f} ms  "
                          f"({statistics.mean(throughputs):5.2f} Mbps)  "
                          f"成功: {len(impl_results)}/{TRIALS_PER_SCENARIO}")
                else:
                    print(f"{impl:20s}: 全部失败")

        # 计算性能提升
        print(f"\n{'='*60}")
        print("性能对比")
        print(f"{'='*60}\n")

        for scenario in scenarios:
            scenario_desc = next(r["scenario_desc"] for r in self.results if r["scenario"] == scenario)

            reno_results = [
                r for r in self.results
                if r["implementation"] == "foggytcp2_reno" and r["scenario"] == scenario and r["success"]
            ]

            cubic_results = [
                r for r in self.results
                if r["implementation"] == "enhanced_cubic" and r["scenario"] == scenario and r["success"]
            ]

            if reno_results and cubic_results:
                reno_avg = statistics.mean([r["duration_ms"] for r in reno_results])
                cubic_avg = statistics.mean([r["duration_ms"] for r in cubic_results])

                improvement = (reno_avg - cubic_avg) / reno_avg * 100

                print(f"{scenario_desc}:")
                print(f"  Reno:  {reno_avg:7.0f} ms")
                print(f"  Cubic: {cubic_avg:7.0f} ms")
                print(f"  提升:  {improvement:+6.1f}% {'✅' if improvement > 0 else '❌'}")
                print()

def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║           TCP 拥塞控制算法性能对比测试                        ║
║                                                              ║
║  对比实现:                                                   ║
║    1. TCP Reno (foggytcp2)                                  ║
║    2. Enhanced Cubic (enhanced_cca)                         ║
╚══════════════════════════════════════════════════════════════╝
    """)

    runner = TestRunner()

    # 编译两个实现
    if not runner.compile_implementation(FOGGYTCP2_DIR, "foggytcp2_reno"):
        print("❌ foggytcp2 编译失败，退出")
        return

    if not runner.compile_implementation(ENHANCED_CCA_DIR, "enhanced_cubic"):
        print("❌ enhanced_cca 编译失败，退出")
        return

    # 测试 Reno
    runner.test_implementation(FOGGYTCP2_DIR, "foggytcp2_reno")

    # 测试 Cubic
    runner.test_implementation(ENHANCED_CCA_DIR, "enhanced_cubic")

    # 保存结果
    csv_file = runner.save_results()

    # 打印摘要
    runner.print_summary()

    print(f"\n下一步:")
    print(f"  1. 查看详细结果: cat {csv_file}")
    print(f"  2. 生成图表: python3 scripts/visualize_results.py {csv_file}")
    print()

if __name__ == "__main__":
    main()
