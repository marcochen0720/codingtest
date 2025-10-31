#!/bin/bash
# Evaluation pipeline for BRTM

set -e  # Exit on error

echo "=========================================="
echo "BRTM Evaluation Pipeline"
echo "=========================================="

# Step 1: Construct candidate sets
echo ""
echo "[1/2] Constructing candidate sets..."
cd eval
python3 candidate_construction.py

# Step 2: Evaluate models
echo ""
echo "[2/2] Evaluating BRTM models..."
python3 evaluation.py

echo ""
echo "=========================================="
echo "Evaluation complete!"
echo "=========================================="
echo ""
echo "Results:"
echo "  - results/evaluation_sample.csv"
echo "  - results/evaluation_sep.csv"
echo ""
echo "See Table 7 format comparison in the output above."
echo ""
