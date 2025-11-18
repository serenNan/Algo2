# Enhanced CCA - 改进的拥塞控制算法

## 目录说明

本文件夹包含改进版的拥塞控制算法实现,独立于原始TCP Reno实现。

```
enhanced_cca/
├── foggytcp/              # 改进算法的源代码
│   ├── src/              # C++源文件
│   │   ├── foggy_function.cc  # 主要修改文件 - 新的拥塞控制逻辑
│   │   ├── foggy_tcp.cc
│   │   ├── foggy_backend.cc
│   │   ├── server.cc
│   │   └── client.cc
│   ├── inc/              # 头文件
│   │   ├── foggy_tcp.h        # 新增Cubic相关数据结构
│   │   ├── foggy_function.h
│   │   └── grading.h          # 修改初始参数
│   ├── build/            # 编译产物
│   ├── Makefile          # 构建配置
│   └── utils/            # 工具脚本
├── scripts/              # 测试和对比脚本
│   ├── benchmark.py          # 性能基准测试
│   ├── compare_with_reno.py  # 与Reno对比
│   └── visualize.py          # 结果可视化
├── results/              # 实验结果
│   ├── baseline/         # Reno基准数据
│   ├── enhanced/         # 改进算法数据
│   ├── comparison/       # 对比结果
│   └── plots/            # 生成的图表
├── testdata/             # 测试文件
│   ├── test_1mb.bin
│   └── test_5mb.bin
├── docs/                 # 文档
│   ├── algorithm_design.md   # 算法设计文档
│   ├── implementation.md     # 实现细节
│   └── evaluation.md         # 性能评估
└── README.md            # 本文件
```

## 算法名称

**Enhanced Cubic Reno (ECR)**

## 主要改进

1. **初始窗口**: 从1 MSS增加到10 MSS (RFC 6928)
2. **拥塞避免**: 使用Cubic函数替代线性增长
3. **窗口减小**: 丢包时窗口缩减比例从0.5改为0.7
4. **慢启动阈值**: 初始值从64 MSS增加到128 MSS

## 快速开始

### 编译

```bash
cd /home/serennan/work/algo2/enhanced_cca/foggytcp
make clean
make foggy
```

### 运行测试

**终端1 - 启动服务器:**
```bash
./server 127.0.0.1 15441 output.bin
```

**终端2 - 启动客户端:**
```bash
./client 127.0.0.1 15441 testdata/test_1mb.bin
```

### 性能对比

```bash
cd /home/serennan/work/algo2/enhanced_cca/scripts
python3 compare_with_reno.py
```

## 开发状态

- [ ] 算法设计完成
- [ ] 代码实现
- [ ] 单元测试
- [ ] 性能基准测试
- [ ] 与Reno对比测试
- [ ] 数据分析和可视化
- [ ] 报告撰写

## 版本历史

- **v0.1** (2025-11-18): 初始项目结构
- **v0.2** (待定): 基础实现
- **v1.0** (待定): 完整实现和测试

## 参考

- TCP Cubic论文: "CUBIC: A New TCP-Friendly High-Speed TCP Variant"
- RFC 6928: "Increasing TCP's Initial Window"
- 原始Reno实现: `/home/serennan/work/algo2/foggytcp2/foggytcp/`

## 联系

如有问题,请参考 `/home/serennan/work/algo2/自定义CCA设计与实现计划.md`
