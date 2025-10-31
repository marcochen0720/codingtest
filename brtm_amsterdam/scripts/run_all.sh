#!/bin/bash
# Complete BRTM reproduction pipeline

set -e  # Exit on error

echo "=========================================="
echo "BRTM Amsterdam Reproduction"
echo "Complete Pipeline"
echo "=========================================="

START_TIME=$(date +%s)

# Navigate to project root
cd "$(dirname "$0")/.."

# Step 1: Data preparation
echo ""
echo "STAGE 1: Data Preparation"
echo "=========================================="
bash scripts/make_data.sh

# Step 2: Training
echo ""
echo "STAGE 2: Model Training"
echo "=========================================="
bash scripts/train.sh

# Step 3: Evaluation
echo ""
echo "STAGE 3: Model Evaluation"
echo "=========================================="
bash scripts/eval.sh

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
echo "=========================================="
echo "Complete pipeline finished!"
echo "Total time: $DURATION seconds"
echo "=========================================="
echo ""
echo "Final results are in:"
echo "  - results/evaluation_sample.csv (BRTM-Sample)"
echo "  - results/evaluation_sep.csv (BRTM-SEP)"
echo ""
echo "See Table 7 comparison in: results/table7_comparison.txt"
echo ""
