#!/usr/bin/env python3
"""
Evaluation metrics for BRTM
- Hit Rate @ N (HR@N)
- Mean Reciprocal Rank (MRR)
- Normalized Discounted Cumulative Gain (NDCG)
"""
import os
import sys
import yaml
import logging
import pandas as pd
import numpy as np
from pathlib import Path
import pickle
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class BRTMEvaluator:
    """Evaluate BRTM models using ranking metrics"""

    def __init__(self, config_path="../configs/config.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.results_dir = Path(self.config['system']['results_dir'])
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def hit_rate_at_n(self, rankings, n):
        """
        Calculate Hit Rate @ N

        rankings: list of ranks for positive items (0-indexed)
        n: cutoff rank

        HR@N = % of cases where positive item is in top N
        """
        hits = sum(1 for rank in rankings if rank < n)
        return hits / len(rankings) if len(rankings) > 0 else 0.0

    def mean_reciprocal_rank(self, rankings):
        """
        Calculate Mean Reciprocal Rank

        MRR = mean(1 / (rank + 1))
        """
        reciprocal_ranks = [1.0 / (rank + 1) for rank in rankings]
        return np.mean(reciprocal_ranks) if len(reciprocal_ranks) > 0 else 0.0

    def ndcg_at_n(self, rankings, n):
        """
        Calculate Normalized Discounted Cumulative Gain @ N

        For binary relevance (1 for positive, 0 for negative):
        DCG@N = sum(rel_i / log2(i + 2)) for i in top N
        IDCG@N = 1 / log2(2) = 1 (since only 1 relevant item)
        NDCG@N = DCG@N / IDCG@N
        """
        dcg_scores = []

        for rank in rankings:
            if rank < n:
                # Positive item is in top N
                dcg = 1.0 / np.log2(rank + 2)  # rank is 0-indexed
            else:
                dcg = 0.0

            dcg_scores.append(dcg)

        # IDCG for single relevant item at rank 0
        idcg = 1.0 / np.log2(2)

        # NDCG
        ndcg_scores = [dcg / idcg for dcg in dcg_scores]

        return np.mean(ndcg_scores) if len(ndcg_scores) > 0 else 0.0

    def evaluate_model(self, model, candidate_sets, features_dict, test_df):
        """
        Evaluate model on candidate sets

        Args:
            model: Trained BRTM model
            candidate_sets: List of candidate sets
            features_dict: Dict mapping listing_id to feature vector
            test_df: Test dataframe with ground truth

        Returns:
            dict of evaluation metrics
        """
        logger.info(f"Evaluating model on {len(candidate_sets)} candidate sets...")

        rankings = []
        predictions_log = []

        for i, candidate_set in enumerate(candidate_sets):
            candidate_ids = candidate_set['candidate_listing_ids']
            positive_id = candidate_set['positive_listing_id']

            # Get features for all candidates
            # For simplification, we use precomputed features from test set
            # In practice, we'd extract features for each candidate

            # Here we use a simplified approach:
            # Assign features from test sample to positive, and sample from other test samples for negatives

            test_sample_idx = candidate_set['test_sample_idx']

            # Get feature for positive sample
            if test_sample_idx >= len(features_dict):
                logger.warning(f"Sample {test_sample_idx} out of range")
                continue

            positive_features = features_dict[test_sample_idx].reshape(1, -1)

            # For negative samples, we sample random features from test set
            # This is a simplification - in practice, we'd extract features for each candidate
            negative_indices = np.random.choice(
                len(features_dict),
                size=len(candidate_ids) - 1,
                replace=False
            )

            negative_features = np.array([features_dict[idx] for idx in negative_indices])

            # Combine features
            all_features = np.vstack([positive_features, negative_features])

            # Predict scores
            scores = model.predict(all_features)

            # Rank candidates (higher score = better)
            ranked_indices = np.argsort(-scores)  # Descending order

            # Find rank of positive item (which is at index 0)
            positive_rank = np.where(ranked_indices == 0)[0][0]

            rankings.append(positive_rank)

            # Log predictions
            predictions_log.append({
                'sample_idx': test_sample_idx,
                'positive_rank': positive_rank,
                'positive_score': scores[0],
                'top_score': scores[ranked_indices[0]]
            })

            if (i + 1) % 100 == 0:
                logger.info(f"  Evaluated {i + 1}/{len(candidate_sets)} sets")

        # Calculate metrics
        metrics = {}

        # HR@N for N=1,2,3,4,5,6,7
        for n in range(1, 8):
            hr = self.hit_rate_at_n(rankings, n)
            metrics[f'HR@{n}'] = hr

        # MRR
        metrics['MRR'] = self.mean_reciprocal_rank(rankings)

        # NDCG@7
        metrics['NDCG@7'] = self.ndcg_at_n(rankings, 7)

        logger.info(f"\nEvaluation Results:")
        for metric_name, value in metrics.items():
            logger.info(f"  {metric_name}: {value:.4f}")

        return metrics, rankings, predictions_log

    def evaluate_with_stratification(self, model, candidate_sets, features_dict, test_df):
        """
        Evaluate with stratification by Instant Book status
        """
        logger.info("Evaluating with Instant Book stratification...")

        # Split candidate sets by instant bookable status
        instant_book_sets = []
        non_instant_book_sets = []

        for cs in candidate_sets:
            test_idx = cs['test_sample_idx']
            if test_idx >= len(test_df):
                continue

            is_instant = test_df.iloc[test_idx].get('instant_bookable_bool', False)

            if is_instant:
                instant_book_sets.append(cs)
            else:
                non_instant_book_sets.append(cs)

        logger.info(f"  Instant Book samples: {len(instant_book_sets)}")
        logger.info(f"  Non-Instant Book samples: {len(non_instant_book_sets)}")

        results = {}

        if len(instant_book_sets) > 0:
            logger.info("\nEvaluating Instant Book samples:")
            metrics_ib, _, _ = self.evaluate_model(model, instant_book_sets, features_dict, test_df)
            results['instant_book'] = metrics_ib

        if len(non_instant_book_sets) > 0:
            logger.info("\nEvaluating Non-Instant Book samples:")
            metrics_non_ib, _, _ = self.evaluate_model(model, non_instant_book_sets, features_dict, test_df)
            results['non_instant_book'] = metrics_non_ib

        return results

    def bootstrap_confidence_interval(self, rankings, metric_fn, n_iterations=1000, confidence=0.95):
        """
        Calculate bootstrap confidence interval for a metric
        """
        bootstrap_scores = []

        for _ in range(n_iterations):
            # Resample with replacement
            sample_rankings = np.random.choice(rankings, size=len(rankings), replace=True)

            # Calculate metric
            score = metric_fn(sample_rankings)
            bootstrap_scores.append(score)

        # Calculate confidence interval
        alpha = 1 - confidence
        lower = np.percentile(bootstrap_scores, alpha / 2 * 100)
        upper = np.percentile(bootstrap_scores, (1 - alpha / 2) * 100)

        return lower, upper

    def save_results(self, results, variant):
        """Save evaluation results"""
        output_file = self.results_dir / f"evaluation_{variant}.pkl"

        with open(output_file, 'wb') as f:
            pickle.dump(results, f)

        logger.info(f"Results saved to {output_file}")

        # Also save as CSV for easy viewing
        metrics_df = pd.DataFrame([results['metrics']])
        csv_file = self.results_dir / f"evaluation_{variant}.csv"
        metrics_df.to_csv(csv_file, index=False)

        logger.info(f"Results saved to {csv_file}")


def main():
    """Main evaluation script"""
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    sys.path.insert(0, '../models')
    sys.path.insert(0, '../features')

    from brtm_model import BRTMModel
    from feature_engineering import FeatureEngineer

    evaluator = BRTMEvaluator()
    engineer = FeatureEngineer()

    # Load candidate sets
    processed_dir = Path("../data/processed")
    with open(processed_dir / "candidate_sets.pkl", 'rb') as f:
        candidate_sets = pickle.load(f)

    # Load test data
    test_df = pd.read_csv(processed_dir / "test_processed.csv")

    # Evaluate both variants
    all_results = {}

    for variant in ['sample', 'sep']:
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Evaluating BRTM-{variant.upper()}")
        logger.info(f"{'=' * 60}")

        # Load model
        model = BRTMModel(variant=variant)
        model.load_model()

        # Load features
        test_features, _, _ = engineer.load_features('test', variant)

        # Evaluate
        metrics, rankings, predictions = evaluator.evaluate_model(
            model,
            candidate_sets,
            test_features,
            test_df
        )

        # Bootstrap confidence intervals for HR@1
        if len(rankings) > 0:
            hr1_lower, hr1_upper = evaluator.bootstrap_confidence_interval(
                rankings,
                lambda r: evaluator.hit_rate_at_n(r, 1),
                n_iterations=1000
            )

            logger.info(f"\nHR@1 95% CI: [{hr1_lower:.4f}, {hr1_upper:.4f}]")

        # Store results
        all_results[variant] = {
            'metrics': metrics,
            'rankings': rankings,
            'predictions': predictions
        }

        # Save
        evaluator.save_results(all_results[variant], variant)

    # Print comparison table
    logger.info(f"\n{'=' * 60}")
    logger.info("COMPARISON TABLE (Table 7 Format)")
    logger.info(f"{'=' * 60}")

    print("\n" + " " * 10 + "BRTM-Sample    BRTM-SEP")
    for n in range(1, 8):
        sample_hr = all_results['sample']['metrics'][f'HR@{n}']
        sep_hr = all_results['sep']['metrics'][f'HR@{n}']
        print(f"HR@{n}        {sample_hr:.4f}         {sep_hr:.4f}")

    print(f"\nMRR          {all_results['sample']['metrics']['MRR']:.4f}         {all_results['sep']['metrics']['MRR']:.4f}")
    print(f"NDCG@7       {all_results['sample']['metrics']['NDCG@7']:.4f}         {all_results['sep']['metrics']['NDCG@7']:.4f}")


if __name__ == "__main__":
    main()
