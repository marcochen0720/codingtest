#!/bin/bash
# Quick test script to verify all modules work

set -e

echo "=========================================="
echo "BRTM Quick Test"
echo "=========================================="

cd "$(dirname "$0")/.."

echo ""
echo "Testing Python modules..."

# Test imports
python3 -c "
import sys
sys.path.insert(0, 'data')
sys.path.insert(0, 'features')
sys.path.insert(0, 'models')
sys.path.insert(0, 'eval')

print('✓ Testing data module imports...')
from download_insideairbnb import InsideAirbnbDownloader
from crawl_bilateral_reviews import BilateralReviewCrawler
from preprocess import DataPreprocessor

print('✓ Testing feature module imports...')
from topic_modeling import BRTMTopicModeler
from feature_engineering import FeatureEngineer

print('✓ Testing model module imports...')
from brtm_model import BRTMModel

print('✓ Testing eval module imports...')
from candidate_construction import CandidateSetConstructor
from evaluation import BRTMEvaluator

print('✓ All modules imported successfully!')
"

echo ""
echo "Testing dependencies..."
python3 -c "
import numpy as np
import pandas as pd
import sklearn
import yaml
import requests
from bs4 import BeautifulSoup

print('✓ numpy:', np.__version__)
print('✓ pandas:', pd.__version__)
print('✓ sklearn:', sklearn.__version__)
print('✓ All dependencies available!')
"

echo ""
echo "Testing configuration..."
python3 -c "
import yaml
with open('configs/config.yaml', 'r') as f:
    config = yaml.safe_load(f)
print('✓ Configuration loaded successfully')
print('  - City:', config['data']['city'])
print('  - Random seed:', config['system']['random_seed'])
print('  - Shared topics:', config['features']['topics']['shared_topics'])
"

echo ""
echo "=========================================="
echo "✓ All tests passed!"
echo "=========================================="
echo ""
echo "Ready to run the full pipeline:"
echo "  bash scripts/run_all.sh"
echo ""
