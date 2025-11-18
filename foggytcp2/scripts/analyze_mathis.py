#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dr. Matt Mathis 假设验证 - 数据分析脚本
执行线性回归、计算相关系数、生成可视化图表
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
from pathlib import Path
import sys

# 设置中文字体支持
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

# ============ 配置参数 ============
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
RESULTS_DIR = PROJECT_ROOT / "results"
INPUT_CSV = RESULTS_DIR / "mathis_data.csv"
OUTPUT_PLOT = RESULTS_DIR / "mathis_plot.png"
OUTPUT_SUMMARY = RESULTS_DIR / "mathis_summary.txt"

# TCP 参数
MSS = 1360  # bytes (实际值可能略有不同,根据头部大小)
RTT = 0.04  # 40ms = 0.04s

# ============ 数据加载 ============

def load_data():
    """加载实验数据"""
    if not INPUT_CSV.exists():
        print(f"[错误] 数据文件不存在: {INPUT_CSV}")
        print("请先运行 experiment_mathis.py 生成数据")
        sys.exit(1)

    df = pd.read_csv(INPUT_CSV)
    print(f"[加载] 成功加载 {len(df)} 条数据记录")
    print(f"\n数据预览:")
    print(df.head())

    return df


# ============ 数据分析 ============

def calculate_statistics(df):
    """计算统计量"""
    print("\n" + "=" * 60)
    print("数据统计分析")
    print("=" * 60)

    # 按丢包率分组统计
    grouped = df.groupby('loss_rate').agg({
        'throughput_mbps': ['mean', 'std', 'min', 'max', 'count'],
        '1_over_sqrt_p': 'first'
    })

    # 重命名列
    grouped.columns = ['平均吞吐量', '标准差', '最小值', '最大值', '样本数', '1/sqrt(p)']

    print("\n按丢包率统计:")
    print(grouped.to_string())

    return grouped


def linear_regression(df):
    """线性回归分析"""
    print("\n" + "=" * 60)
    print("线性回归分析")
    print("=" * 60)

    # 使用所有数据点进行回归
    x = df['1_over_sqrt_p'].values
    y = df['throughput_mbps'].values

    # 执行线性回归
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

    print(f"\n回归方程: throughput = {slope:.6f} × (1/√p) + {intercept:.6f}")
    print(f"斜率 (slope): {slope:.6f}")
    print(f"截距 (intercept): {intercept:.6f}")
    print(f"R² (决定系数): {r_value**2:.6f}")
    print(f"P 值: {p_value:.2e}")
    print(f"标准误差: {std_err:.6f}")

    # 计算常数 C
    # 公式: throughput = (MSS/RTT) × (C/√p)
    # 变形: throughput = (MSS/RTT) × C × (1/√p)
    # 所以: slope = (MSS/RTT) × C
    # 因此: C = slope × RTT / MSS

    # 转换单位: MSS 是字节, RTT 是秒, throughput 是 Mbps
    # slope 的单位是 Mbps / (1/√p) = Mbps
    # MSS/RTT 的单位是 bytes/s = bytes/s
    # 需要统一单位

    # 方法:
    # throughput (Mbps) = slope × (1/√p)
    # throughput (bps) = slope × 1e6 × (1/√p)
    # 理论公式: throughput (bps) = (MSS/RTT) × C × (1/√p)
    # 对比: slope × 1e6 = (MSS/RTT) × C
    # C = (slope × 1e6 × RTT) / MSS

    C = (slope * 1e6 * RTT) / MSS

    print(f"\n常数 C 的计算:")
    print(f"  公式: C = (slope × 1e6 × RTT) / MSS")
    print(f"  C = ({slope:.6f} × 1e6 × {RTT}) / {MSS}")
    print(f"  C = {C:.6f}")

    return {
        'slope': slope,
        'intercept': intercept,
        'r_squared': r_value**2,
        'r_value': r_value,
        'p_value': p_value,
        'std_err': std_err,
        'C': C
    }


def correlation_analysis(df):
    """相关性分析"""
    print("\n" + "=" * 60)
    print("皮尔逊相关系数分析")
    print("=" * 60)

    x = df['1_over_sqrt_p'].values
    y = df['throughput_mbps'].values

    # 计算皮尔逊相关系数
    pearson_r, pearson_p = stats.pearsonr(x, y)

    print(f"\n皮尔逊相关系数 r: {pearson_r:.6f}")
    print(f"P 值: {pearson_p:.2e}")

    # 判断相关性强度
    if abs(pearson_r) > 0.9:
        strength = "强相关"
    elif abs(pearson_r) > 0.7:
        strength = "中等相关"
    else:
        strength = "弱相关"

    print(f"相关性强度: {strength}")

    # 显著性检验
    if pearson_p < 0.05:
        print(f"显著性: 显著 (p < 0.05)")
    else:
        print(f"显著性: 不显著 (p >= 0.05)")

    return {
        'pearson_r': pearson_r,
        'pearson_p': pearson_p,
        'strength': strength
    }


# ============ 可视化 ============

def create_plot(df, grouped, regression_results, correlation_results):
    """创建回归分析图表"""
    print("\n" + "=" * 60)
    print("生成可视化图表")
    print("=" * 60)

    fig, ax = plt.subplots(figsize=(12, 8))

    # 1. 散点图 - 所有数据点
    ax.scatter(df['1_over_sqrt_p'], df['throughput_mbps'],
               alpha=0.3, s=50, c='steelblue',
               label='实验数据点', edgecolors='navy', linewidth=0.5)

    # 2. 平均值折线图
    ax.plot(grouped['1/sqrt(p)'], grouped['平均吞吐量'],
            'o-', linewidth=2.5, markersize=10, color='darkorange',
            label='平均吞吐量', markeredgecolor='darkred', markeredgewidth=1.5)

    # 添加误差棒
    ax.errorbar(grouped['1/sqrt(p)'], grouped['平均吞吐量'],
                yerr=grouped['标准差'], fmt='none', ecolor='coral',
                elinewidth=2, capsize=5, alpha=0.6)

    # 3. 回归线
    x_line = np.linspace(df['1_over_sqrt_p'].min(), df['1_over_sqrt_p'].max(), 100)
    y_line = regression_results['slope'] * x_line + regression_results['intercept']
    ax.plot(x_line, y_line, 'r--', linewidth=3,
            label=f"回归线: y = {regression_results['slope']:.4f}x + {regression_results['intercept']:.4f}")

    # 标签和标题
    ax.set_xlabel('1/√p', fontsize=16, fontweight='bold')
    ax.set_ylabel('吞吐量 (Mbps)', fontsize=16, fontweight='bold')
    ax.set_title('Dr. Matt Mathis 假设验证\nTCP Reno 吞吐量 vs 1/√p',
                 fontsize=18, fontweight='bold', pad=20)

    # 图例
    ax.legend(fontsize=12, loc='upper left', framealpha=0.9)

    # 网格
    ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.8)

    # 添加统计信息文本框
    textstr = '\n'.join([
        f"常数 C = {regression_results['C']:.4f}",
        f"R² = {regression_results['r_squared']:.4f}",
        f"Pearson r = {correlation_results['pearson_r']:.4f}",
        f"",
        f"MSS = {MSS} bytes",
        f"RTT = {RTT*1000:.0f} ms",
        f"样本数 = {len(df)}"
    ])

    props = dict(boxstyle='round', facecolor='wheat', alpha=0.8, edgecolor='black', linewidth=2)
    ax.text(0.98, 0.02, textstr, transform=ax.transAxes,
            fontsize=12, verticalalignment='bottom', horizontalalignment='right',
            bbox=props, family='monospace')

    # 调整布局
    plt.tight_layout()

    # 保存图表
    plt.savefig(OUTPUT_PLOT, dpi=300, bbox_inches='tight')
    print(f"\n[保存] 图表已保存到: {OUTPUT_PLOT}")

    # 显示图表
    # plt.show()  # 取消注释以显示图表


# ============ 生成摘要报告 ============

def generate_summary(df, grouped, regression_results, correlation_results):
    """生成文本摘要报告"""
    print("\n" + "=" * 60)
    print("生成摘要报告")
    print("=" * 60)

    with open(OUTPUT_SUMMARY, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("Dr. Matt Mathis 假设验证 - 实验结果摘要\n")
        f.write("=" * 60 + "\n\n")

        # 实验配置
        f.write("实验配置\n")
        f.write("-" * 60 + "\n")
        f.write(f"MSS: {MSS} bytes\n")
        f.write(f"RTT: {RTT*1000:.0f} ms\n")
        f.write(f"总样本数: {len(df)}\n")
        f.write(f"丢包率种类: {df['loss_rate'].nunique()}\n")
        f.write(f"每个丢包率重复次数: {df.groupby('loss_rate').size().mode()[0]}\n\n")

        # 统计数据
        f.write("统计数据\n")
        f.write("-" * 60 + "\n")
        f.write(grouped.to_string())
        f.write("\n\n")

        # 线性回归结果
        f.write("线性回归结果\n")
        f.write("-" * 60 + "\n")
        f.write(f"回归方程: throughput = {regression_results['slope']:.6f} × (1/√p) + {regression_results['intercept']:.6f}\n")
        f.write(f"斜率: {regression_results['slope']:.6f}\n")
        f.write(f"截距: {regression_results['intercept']:.6f}\n")
        f.write(f"R² (决定系数): {regression_results['r_squared']:.6f}\n")
        f.write(f"P 值: {regression_results['p_value']:.2e}\n")
        f.write(f"标准误差: {regression_results['std_err']:.6f}\n")
        f.write(f"\n常数 C: {regression_results['C']:.6f}\n\n")

        # 相关性分析
        f.write("皮尔逊相关系数分析\n")
        f.write("-" * 60 + "\n")
        f.write(f"皮尔逊相关系数 r: {correlation_results['pearson_r']:.6f}\n")
        f.write(f"P 值: {correlation_results['pearson_p']:.2e}\n")
        f.write(f"相关性强度: {correlation_results['strength']}\n")
        f.write(f"显著性: {'显著' if correlation_results['pearson_p'] < 0.05 else '不显著'}\n\n")

        # 结论
        f.write("结论\n")
        f.write("-" * 60 + "\n")

        # 判断假设支持度
        if regression_results['r_squared'] > 0.8 and abs(correlation_results['pearson_r']) > 0.9:
            support = "强烈支持"
        elif regression_results['r_squared'] > 0.6 and abs(correlation_results['pearson_r']) > 0.7:
            support = "部分支持"
        else:
            support = "不支持"

        f.write(f"假设支持度: {support} Dr. Mathis 假设\n\n")

        f.write("理由:\n")
        f.write(f"1. R² = {regression_results['r_squared']:.4f}, ")
        if regression_results['r_squared'] > 0.8:
            f.write("表明线性拟合良好\n")
        elif regression_results['r_squared'] > 0.6:
            f.write("表明线性拟合一般\n")
        else:
            f.write("表明线性拟合较差\n")

        f.write(f"2. 皮尔逊相关系数 r = {correlation_results['pearson_r']:.4f}, ")
        f.write(f"表明 {correlation_results['strength']}\n")

        f.write(f"3. 常数 C = {regression_results['C']:.4f}, ")
        if 0.5 <= regression_results['C'] <= 2.0:
            f.write("符合理论预期范围 (0.5-2.0)\n")
        else:
            f.write("不在理论预期范围 (0.5-2.0)\n")

    print(f"\n[保存] 摘要报告已保存到: {OUTPUT_SUMMARY}")


# ============ 主函数 ============

def main():
    print("=" * 60)
    print("Dr. Matt Mathis 假设验证 - 数据分析")
    print("=" * 60)

    # 1. 加载数据
    df = load_data()

    # 2. 统计分析
    grouped = calculate_statistics(df)

    # 3. 线性回归
    regression_results = linear_regression(df)

    # 4. 相关性分析
    correlation_results = correlation_analysis(df)

    # 5. 生成图表
    create_plot(df, grouped, regression_results, correlation_results)

    # 6. 生成摘要报告
    generate_summary(df, grouped, regression_results, correlation_results)

    print("\n" + "=" * 60)
    print("分析完成!")
    print("=" * 60)
    print(f"\n生成的文件:")
    print(f"  - 图表: {OUTPUT_PLOT}")
    print(f"  - 摘要: {OUTPUT_SUMMARY}")
    print(f"\n关键结果:")
    print(f"  - 常数 C: {regression_results['C']:.4f}")
    print(f"  - R²: {regression_results['r_squared']:.4f}")
    print(f"  - Pearson r: {correlation_results['pearson_r']:.4f}")


if __name__ == "__main__":
    main()
