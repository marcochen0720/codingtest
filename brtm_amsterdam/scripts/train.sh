#!/bin/bash
# Training pipeline for BRTM

set -e  # Exit on error

echo "=========================================="
echo "BRTM Training Pipeline"
echo "=========================================="

# Step 1: Topic modeling
echo ""
echo "[1/3] Training topic models..."
cd features
python3 topic_modeling.py

# Step 2: Feature engineering
echo ""
echo "[2/3] Extracting features..."
python3 feature_engineering.py

# Step 3: Train BRTM models
echo ""
echo "[3/3] Training BRTM models..."
cd ../models
python3 brtm_model.py

echo ""
echo "=========================================="
echo "Training complete!"
echo "=========================================="
echo ""
echo "Trained models:"
echo "  - results/brtm_sample_model.pkl"
echo "  - results/brtm_sep_model.pkl"
echo ""
echo "Topic models:"
echo "  - cache/topic_models_sample.pkl"
echo "  - cache/topic_models_sep.pkl"
echo ""
