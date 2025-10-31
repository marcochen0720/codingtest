#!/bin/bash
# Data preparation pipeline for BRTM

set -e  # Exit on error

echo "=========================================="
echo "BRTM Data Preparation Pipeline"
echo "=========================================="

# Step 1: Download Inside Airbnb data
echo ""
echo "[1/3] Downloading Inside Airbnb data..."
cd data
python3 download_insideairbnb.py

# Step 2: Crawl bilateral reviews
echo ""
echo "[2/3] Crawling bilateral reviews (host responses)..."
python3 crawl_bilateral_reviews.py

# Step 3: Preprocess and clean data
echo ""
echo "[3/3] Preprocessing and cleaning data..."
python3 preprocess.py

echo ""
echo "=========================================="
echo "Data preparation complete!"
echo "=========================================="
echo ""
echo "Output files:"
echo "  - data/processed/listings_processed.csv"
echo "  - data/processed/train_processed.csv"
echo "  - data/processed/val_processed.csv"
echo "  - data/processed/test_processed.csv"
echo "  - data/processed/split_dates.json"
echo ""
