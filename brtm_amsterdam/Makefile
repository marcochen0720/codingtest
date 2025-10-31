.PHONY: help setup test data train eval all clean

help:
	@echo "BRTM Amsterdam Reproduction - Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  make setup    - Setup conda environment"
	@echo "  make test     - Run quick tests"
	@echo "  make data     - Prepare data"
	@echo "  make train    - Train models"
	@echo "  make eval     - Evaluate models"
	@echo "  make all      - Run complete pipeline"
	@echo "  make clean    - Clean generated files"
	@echo ""

setup:
	@echo "Setting up environment..."
	conda env create -f environment.yml
	@echo "Activate with: conda activate brtm_amsterdam"

test:
	@echo "Running quick tests..."
	bash scripts/quick_test.sh

data:
	@echo "Preparing data..."
	bash scripts/make_data.sh

train:
	@echo "Training models..."
	bash scripts/train.sh

eval:
	@echo "Evaluating models..."
	bash scripts/eval.sh

all:
	@echo "Running complete pipeline..."
	bash scripts/run_all.sh

clean:
	@echo "Cleaning generated files..."
	rm -rf data/raw/*
	rm -rf data/crawled/*
	rm -rf data/processed/*
	rm -rf cache/*
	rm -rf results/*
	@echo "Clean complete!"

results:
	@echo "Displaying results..."
	@echo ""
	@echo "=== BRTM-Sample Results ==="
	@cat results/evaluation_sample.csv 2>/dev/null || echo "No results yet. Run 'make all' first."
	@echo ""
	@echo "=== BRTM-SEP Results ==="
	@cat results/evaluation_sep.csv 2>/dev/null || echo "No results yet. Run 'make all' first."
	@echo ""
