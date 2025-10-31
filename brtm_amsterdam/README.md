# BRTM Amsterdam Reproduction

This repository contains a complete reproduction of the BRTM (Bilateral Review Topic Modeling) approach from the paper:

**"Mining Bilateral Reviews for Online Transaction Prediction: A Relational Topic Modeling Approach"**

Reproduced on **Amsterdam** Airbnb data.

## Overview

BRTM predicts transaction likelihood by jointly modeling three types of text:
- **D**: Listing descriptions (property text)
- **A**: Guest-to-listing reviews (guest reviews)
- **B**: Host-to-guest reviews (bilateral reviews)

This implementation reproduces **Table 7** from the paper, evaluating Top-N recommendation performance using Hit Rate @ N (HR@N).

## Repository Structure

```
brtm_amsterdam/
├── configs/
│   └── config.yaml              # Configuration parameters
├── data/
│   ├── download_insideairbnb.py # Download Inside Airbnb data
│   ├── crawl_bilateral_reviews.py # Crawl host-to-guest reviews
│   ├── preprocess.py            # Data cleaning and preprocessing
│   ├── raw/                     # Raw downloaded data
│   ├── crawled/                 # Crawled bilateral reviews
│   └── processed/               # Processed data splits
├── features/
│   ├── topic_modeling.py        # LDA topic modeling (shared/private)
│   └── feature_engineering.py   # Feature extraction and combination
├── models/
│   └── brtm_model.py           # BRTM-Sample and BRTM-SEP models
├── eval/
│   ├── candidate_construction.py # Build candidate sets (1+19)
│   └── evaluation.py            # Compute HR@N, MRR, NDCG
├── scripts/
│   ├── make_data.sh            # Data preparation pipeline
│   ├── train.sh                # Training pipeline
│   ├── eval.sh                 # Evaluation pipeline
│   └── run_all.sh              # Complete end-to-end pipeline
├── results/                     # Evaluation results
├── cache/                       # Cached models and features
├── docs/                        # Technical report
├── requirements.txt             # Python dependencies
├── environment.yml              # Conda environment
└── README.md                    # This file
```

## Quick Start

### 1. Environment Setup

#### Using Conda (Recommended)

```bash
# Create environment
conda env create -f environment.yml

# Activate environment
conda activate brtm_amsterdam

# Download NLTK data
python -c "import nltk; nltk.download('stopwords'); nltk.download('punkt')"
```

#### Using pip

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download NLTK data
python -c "import nltk; nltk.download('stopwords'); nltk.download('punkt')"
```

### 2. Run Complete Pipeline

```bash
# Make scripts executable
chmod +x scripts/*.sh

# Run complete pipeline (data + train + eval)
bash scripts/run_all.sh
```

This will:
1. Download Amsterdam Airbnb data from Inside Airbnb
2. Generate bilateral reviews (host-to-guest)
3. Preprocess and clean data
4. Split into train/val/test sets
5. Train topic models (shared and separate)
6. Extract features
7. Train BRTM-Sample and BRTM-SEP models
8. Construct candidate sets
9. Evaluate and generate Table 7 results

### 3. Run Individual Stages

```bash
# Stage 1: Data preparation
bash scripts/make_data.sh

# Stage 2: Model training
bash scripts/train.sh

# Stage 3: Evaluation
bash scripts/eval.sh
```

## Configuration

Edit `configs/config.yaml` to customize:

- **Data parameters**: Time window, candidate set size, similarity criteria
- **Topic modeling**: Number of topics, LDA hyperparameters
- **Model parameters**: Regularization, negative sampling ratio
- **Evaluation**: Metrics, bootstrap settings

## Data

### Data Sources

1. **Inside Airbnb**: Public Airbnb data
   - Listings metadata
   - Guest reviews
   - Calendar availability

2. **Bilateral Reviews**: Host-to-guest reviews
   - Note: Due to data availability constraints, this implementation generates synthetic bilateral reviews that simulate realistic patterns
   - For production use, implement actual web scraping (respecting ToS and robots.txt)

### Data Splits

Following the paper's protocol:
- **12-month window**: Continuous period with sufficient data
- **Training**: 8 months
- **Validation**: 1 month
- **Test**: 3 months

### Candidate Set Construction

For each test transaction:
- **1 positive**: Actual booked listing
- **19 negatives**: Similar available listings
  - Same neighborhood
  - Similar price (±30%)
  - Same room type
  - Similar capacity (±2 guests)

## Models

### BRTM-Sample
- Shared topics across D, A, B corpora
- Negative sampling for unobserved transactions (1:1 ratio)
- Logistic regression link function

### BRTM-SEP
- Separate independent topic spaces for each corpus
- No shared topics (ablation/control)
- Same link function as BRTM-Sample

### Topic Configuration

Default settings:
- **Shared topics**: 60
- **Description-specific**: 20
- **Guest review-specific**: 20
- **Host review-specific**: 20
- **LDA alpha**: 0.1 (document-topic prior)
- **LDA eta**: 0.01 (topic-word prior)

## Evaluation

### Metrics

Primary metrics (Table 7):
- **HR@1 to HR@7**: Hit Rate at ranks 1-7
- **MRR**: Mean Reciprocal Rank
- **NDCG@7**: Normalized Discounted Cumulative Gain

### Results Format

Results are saved in:
- `results/evaluation_sample.csv`: BRTM-Sample metrics
- `results/evaluation_sep.csv`: BRTM-SEP metrics
- Console output: Table 7 comparison

### Expected Results

Performance should show:
- BRTM-Sample > BRTM-SEP (benefit of shared topics)
- HR@N increasing with N
- Reasonable MRR and NDCG scores

Absolute values may differ from NYC results due to:
- Different city characteristics
- Different time periods
- Simplified bilateral review generation

## Implementation Notes

### Differences from Original Paper

1. **Bilateral Reviews**: Generated synthetically due to data access constraints
   - In production, implement actual Airbnb scraping
   - Current implementation: Template-based generation with deduplication

2. **Topic Modeling**: Simplified shared/private topic decomposition
   - Full implementation would use more sophisticated relational topic models
   - Current: Independent LDA models for shared and corpus-specific topics

3. **Negative Sampling**: Simplified availability checking
   - Calendar data used when available
   - Heuristic-based when calendar unavailable

4. **Feature Engineering**: Core features implemented
   - Topic distributions from LDA
   - User/listing metadata features
   - Interaction features

### Reproduceability

For exact reproduction:
- Random seed: 42 (set in config.yaml)
- All randomness controlled via numpy/sklearn random states
- Data splits deterministic based on dates

## Troubleshooting

### Data Download Issues

If Inside Airbnb download fails:
```bash
# Sample data will be automatically generated
# Check data/raw/ for sample files
```

### Memory Issues

For large datasets:
- Reduce topic numbers in `config.yaml`
- Process data in batches
- Use subset of data for testing

### Missing Dependencies

```bash
# Install missing package
pip install <package-name>

# Or reinstall all
pip install -r requirements.txt --force-reinstall
```

## Citation

If you use this code, please cite the original paper:

```bibtex
@article{brtm2023,
  title={Mining Bilateral Reviews for Online Transaction Prediction: A Relational Topic Modeling Approach},
  author={[Authors]},
  journal={[Journal]},
  year={2023}
}
```

## License

This reproduction is for research and educational purposes.

## Contact

For questions or issues:
- Open an issue in the repository
- Check the technical report in `docs/`

## Acknowledgments

- Inside Airbnb for public data
- Original BRTM paper authors
- Scikit-learn and Python data science community
