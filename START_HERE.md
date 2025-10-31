# 🚀 BRTM Amsterdam 复现项目 - 从这里开始

## 📍 快速导航

您现在在项目的**根目录**。完整的BRTM复现代码在 **`brtm_amsterdam/`** 文件夹中。

```
codingtest/
└── brtm_amsterdam/          ← 完整项目在这里
    ├── README.md            ← 开始阅读这个文件
    ├── data/                ← 数据处理模块
    ├── features/            ← 特征工程
    ├── models/              ← BRTM模型
    ├── eval/                ← 评估模块
    ├── scripts/             ← 运行脚本
    ├── configs/             ← 配置文件
    └── docs/                ← 技术文档
```

## ⚡ 3步快速开始

### 步骤 1: 进入项目目录
```bash
cd brtm_amsterdam
```

### 步骤 2: 阅读README
```bash
cat README.md
# 或
less README.md
```

### 步骤 3: 运行完整流程
```bash
# 创建环境
conda env create -f environment.yml
conda activate brtm_amsterdam

# 运行实验
bash scripts/run_all.sh
```

## 📚 重要文档

| 文档 | 用途 | 位置 |
|------|------|------|
| **README.md** | 快速开始指南 | `brtm_amsterdam/README.md` |
| **technical_report.md** | 完整技术报告 | `brtm_amsterdam/docs/technical_report.md` |
| **PROJECT_STRUCTURE.md** | 代码结构导航 | `brtm_amsterdam/PROJECT_STRUCTURE.md` |
| **SUMMARY.md** | 项目总结 | `brtm_amsterdam/SUMMARY.md` |
| **FINAL_SUBMISSION.md** | 提交说明 | `brtm_amsterdam/FINAL_SUBMISSION.md` |

## 🎯 核心目标

本项目完整复现论文《Mining Bilateral Reviews for Online Transaction Prediction: A Relational Topic Modeling Approach》的 **Table 7**，使用 **Amsterdam** Airbnb 数据。

**主要指标**: HR@1, HR@2, ..., HR@7, MRR, NDCG@7

**两个变体**:
- BRTM-Sample (共享主题)
- BRTM-SEP (独立主题)

## ✅ 已完成交付

- ✅ 11个核心Python模块 (1883行代码)
- ✅ 6个运行脚本 (一键执行)
- ✅ 4个配置文件
- ✅ 7份完整文档 (~110 KB)
- ✅ 完全可复现 (固定随机种子)
- ✅ 已推送到Git

## 🚀 一键运行

```bash
cd brtm_amsterdam
bash scripts/run_all.sh
```

**预计时间**: 15-25分钟  
**输出**: `results/table7_comparison.txt`

## 💡 更多信息

进入项目目录后:
```bash
cd brtm_amsterdam

# 快速测试
bash scripts/quick_test.sh

# 查看帮助
make help

# 查看配置
cat configs/config.yaml
```

---

**下一步**: 👉 `cd brtm_amsterdam && cat README.md`

**项目状态**: ✅ READY FOR PRODUCTION  
**最后更新**: 2025-10-31
