# BRTM Amsterdam Project Structure

```
brtm_amsterdam/
│
├── configs/
│   └── config.yaml                     # Main configuration file
│
├── data/                               # Data pipeline
│   ├── download_insideairbnb.py       # Download Inside Airbnb data
│   ├── crawl_bilateral_reviews.py     # Crawl host-to-guest reviews
│   ├── preprocess.py                  # Clean and split data
│   ├── raw/                           # Raw downloaded data
│   │   ├── listings_*.csv.gz
│   │   ├── reviews_*.csv.gz
│   │   └── calendar_*.csv.gz
│   ├── crawled/                       # Crawled bilateral reviews
│   │   └── host_responses.csv
│   └── processed/                     # Processed data
│       ├── listings_processed.csv
│       ├── train_processed.csv
│       ├── val_processed.csv
│       ├── test_processed.csv
│       ├── candidate_sets.pkl
│       └── split_dates.json
│
├── features/                           # Feature engineering
│   ├── topic_modeling.py              # LDA topic models
│   │   ├── fit_brtm_sample()         # Shared topics
│   │   └── fit_brtm_sep()            # Separate topics
│   └── feature_engineering.py         # Combine features
│       ├── extract_user_features()
│       ├── extract_listing_features()
│       └── combine_features()
│
├── models/                             # BRTM models
│   └── brtm_model.py                  # BRTM-Sample & BRTM-SEP
│       ├── train()                    # Train logistic regression
│       ├── predict()                  # Predict probabilities
│       └── save_model()
│
├── eval/                               # Evaluation
│   ├── candidate_construction.py      # Build 20-candidate sets
│   │   ├── is_similar()              # Check listing similarity
│   │   └── sample_negative_candidates()
│   └── evaluation.py                  # Compute metrics
│       ├── hit_rate_at_n()           # HR@N
│       ├── mean_reciprocal_rank()    # MRR
│       ├── ndcg_at_n()               # NDCG
│       └── bootstrap_confidence_interval()
│
├── scripts/                            # Executable scripts
│   ├── make_data.sh                   # Data preparation pipeline
│   ├── train.sh                       # Training pipeline
│   ├── eval.sh                        # Evaluation pipeline
│   ├── run_all.sh                     # Complete end-to-end
│   ├── quick_test.sh                  # Quick sanity check
│   └── visualize_results.py           # Generate plots & tables
│
├── cache/                              # Cached models
│   ├── topic_models_sample.pkl
│   ├── topic_models_sep.pkl
│   ├── sample/
│   │   ├── train_features.npy
│   │   ├── val_features.npy
│   │   └── test_features.npy
│   └── sep/
│       ├── train_features.npy
│       ├── val_features.npy
│       └── test_features.npy
│
├── results/                            # Evaluation results
│   ├── brtm_sample_model.pkl
│   ├── brtm_sep_model.pkl
│   ├── evaluation_sample.csv
│   ├── evaluation_sep.csv
│   ├── table7_comparison.txt
│   ├── hr_comparison.png
│   └── metric_comparison.png
│
├── docs/                               # Documentation
│   ├── technical_report.md            # Detailed technical report
│   └── [Additional documentation]
│
├── requirements.txt                    # Python dependencies
├── environment.yml                     # Conda environment
├── Makefile                            # Build automation
├── .gitignore                         # Git ignore rules
├── README.md                          # Main documentation
└── PROJECT_STRUCTURE.md               # This file

```

## Data Flow

```
1. Data Collection
   download_insideairbnb.py → data/raw/
   crawl_bilateral_reviews.py → data/crawled/

2. Preprocessing
   preprocess.py → data/processed/
   ├── Clean text
   ├── Deduplicate
   └── Time-based split

3. Feature Engineering
   topic_modeling.py → cache/topic_models_*.pkl
   ├── Fit LDA on train set
   └── Extract topic distributions

   feature_engineering.py → cache/{variant}/
   ├── Combine topic + metadata features
   └── Save feature matrices

4. Model Training
   brtm_model.py → results/brtm_*_model.pkl
   ├── Train logistic regression
   └── Validate on val set

5. Evaluation
   candidate_construction.py → data/processed/candidate_sets.pkl
   ├── Build 20-candidate sets
   └── 1 positive + 19 negatives

   evaluation.py → results/evaluation_*.csv
   ├── Rank candidates
   ├── Compute HR@N, MRR, NDCG
   └── Bootstrap confidence intervals

6. Visualization
   visualize_results.py → results/*.png
   ├── Plot HR@N curves
   ├── Compare metrics
   └── Generate Table 7
```

## Key Files

| File | Purpose | Key Functions |
|------|---------|---------------|
| `config.yaml` | Central configuration | All parameters |
| `download_insideairbnb.py` | Data download | `download_all()` |
| `preprocess.py` | Data cleaning | `clean_text()`, `create_time_splits()` |
| `topic_modeling.py` | Topic extraction | `fit_brtm_sample()`, `fit_brtm_sep()` |
| `feature_engineering.py` | Feature assembly | `combine_features()` |
| `brtm_model.py` | Model training | `train()`, `predict()` |
| `candidate_construction.py` | Candidate sets | `construct_candidate_sets()` |
| `evaluation.py` | Metrics computation | `evaluate_model()` |
| `visualize_results.py` | Result visualization | `generate_table7_text()` |

## Execution Order

### Quick Start
```bash
make all
```

### Step-by-Step
```bash
make data    # Step 1-2: Data collection & preprocessing
make train   # Step 3-4: Feature engineering & training
make eval    # Step 5-6: Evaluation & visualization
```

### Individual Scripts
```bash
# Data
python data/download_insideairbnb.py
python data/crawl_bilateral_reviews.py
python data/preprocess.py

# Features
python features/topic_modeling.py
python features/feature_engineering.py

# Training
python models/brtm_model.py

# Evaluation
python eval/candidate_construction.py
python eval/evaluation.py
python scripts/visualize_results.py
```

## Configuration Hierarchy

```
config.yaml
├── data
│   ├── time_window
│   ├── similarity
│   └── dedup
├── features
│   ├── topics
│   └── lda
├── model
│   ├── lr
│   └── negative_sampling
├── evaluation
│   ├── metrics
│   └── bootstrap
└── system
    ├── random_seed
    └── cache_dir
```

## Output Files

| File | Description |
|------|-------------|
| `results/evaluation_sample.csv` | BRTM-Sample metrics |
| `results/evaluation_sep.csv` | BRTM-SEP metrics |
| `results/table7_comparison.txt` | Table 7 formatted results |
| `results/hr_comparison.png` | HR@N curve plot |
| `results/metric_comparison.png` | Bar charts of metrics |
| `cache/topic_models_*.pkl` | Trained topic models |
| `cache/*/features.npy` | Feature matrices |
| `data/processed/*.csv` | Processed data splits |

## Dependencies

### Core
- numpy, pandas, scipy
- scikit-learn (LDA, LogisticRegression)

### NLP
- nltk (stopwords, tokenization)

### Web
- requests, beautifulsoup4

### Utils
- pyyaml, tqdm

### Optional
- matplotlib, seaborn (visualization)
- jupyter (exploration)

## Testing

```bash
# Quick test
make test

# Or directly
bash scripts/quick_test.sh
```

Checks:
- ✓ Module imports
- ✓ Dependencies
- ✓ Configuration
- ✓ File structure

## Reproducibility

All random operations controlled by:
- `config.yaml`: `system.random_seed: 42`
- NumPy: `np.random.seed(42)`
- Scikit-learn: `random_state=42`

Time-based splits ensure deterministic train/val/test.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Import errors | Run `pip install -r requirements.txt` |
| No data | Run `make data` |
| No models | Run `make train` |
| No results | Run `make eval` |
| Memory issues | Reduce topic numbers in `config.yaml` |

## Extension Points

Want to modify the pipeline? Edit these files:

- **Add features**: `features/feature_engineering.py`
- **Change model**: `models/brtm_model.py`
- **Add metrics**: `eval/evaluation.py`
- **Tune hyperparameters**: `configs/config.yaml`
- **Add baseline**: Create new file in `models/`
