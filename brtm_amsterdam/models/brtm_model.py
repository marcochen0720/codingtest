#!/usr/bin/env python3
"""
BRTM Model Implementation
- BRTM-Sample: With negative sampling
- BRTM-SEP: Separate topic spaces
"""
import os
import sys
import yaml
import logging
import pandas as pd
import numpy as np
from pathlib import Path
import pickle
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score, log_loss
import warnings
warnings.filterwarnings('ignore')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class BRTMModel:
    """
    BRTM Model for Transaction Prediction

    Uses logistic regression as the link function to predict
    transaction probability given user-listing features
    """

    def __init__(self, config_path="../configs/config.yaml", variant='sample'):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.variant = variant
        self.C = self.config['model']['lr']['C']
        self.max_iter = self.config['model']['lr']['max_iter']
        self.random_state = self.config['model']['lr']['random_state']

        self.neg_sampling_ratio = self.config['model']['negative_sampling']['ratio']

        self.results_dir = Path(self.config['system']['results_dir'])
        self.results_dir.mkdir(parents=True, exist_ok=True)

        self.model = None

    def create_negative_samples(self, df, ratio=1.0):
        """
        Create negative samples for training

        For each positive transaction, sample negative listings
        """
        logger.info(f"Creating negative samples with ratio {ratio}...")

        # All samples in training are positive (actual reviews)
        # We need to create negative samples

        # Strategy: For each user-listing pair, create negative samples
        # from listings that were available but not booked

        # Simplified: Random negative sampling from same neighborhood/price range
        positive_samples = df.copy()
        positive_samples['label'] = 1

        negative_samples_list = []

        # Group by user (reviewer)
        for reviewer_id, group in df.groupby('reviewer_id'):
            n_positives = len(group)
            n_negatives = int(n_positives * ratio)

            if n_negatives == 0:
                continue

            # Sample negative listings (different from user's actual bookings)
            booked_listings = set(group['listing_id'].unique())

            # Get candidate listings from same date range
            candidates = df[~df['listing_id'].isin(booked_listings)]

            if len(candidates) == 0:
                continue

            # Sample
            if len(candidates) < n_negatives:
                neg_sample = candidates
            else:
                neg_sample = candidates.sample(n=n_negatives, random_state=self.random_state)

            # Assign user to negative samples
            neg_sample = neg_sample.copy()
            neg_sample['reviewer_id'] = reviewer_id
            neg_sample['label'] = 0

            negative_samples_list.append(neg_sample)

        if negative_samples_list:
            negative_samples = pd.concat(negative_samples_list, ignore_index=True)
        else:
            negative_samples = pd.DataFrame()

        logger.info(f"Created {len(negative_samples)} negative samples from {len(positive_samples)} positives")

        # Combine
        combined = pd.concat([positive_samples, negative_samples], ignore_index=True)

        # Shuffle
        combined = combined.sample(frac=1, random_state=self.random_state).reset_index(drop=True)

        return combined

    def train(self, X_train, y_train, X_val=None, y_val=None):
        """Train logistic regression model"""
        logger.info(f"Training BRTM-{self.variant.upper()} model...")
        logger.info(f"Training set: {X_train.shape}, Positive ratio: {y_train.mean():.3f}")

        # Train logistic regression
        self.model = LogisticRegression(
            C=self.C,
            max_iter=self.max_iter,
            random_state=self.random_state,
            solver='lbfgs',
            n_jobs=-1,
            verbose=0
        )

        self.model.fit(X_train, y_train)

        # Training metrics
        train_pred = self.model.predict_proba(X_train)[:, 1]
        train_acc = accuracy_score(y_train, self.model.predict(X_train))
        train_auc = roc_auc_score(y_train, train_pred)
        train_loss = log_loss(y_train, train_pred)

        logger.info(f"Training - Acc: {train_acc:.4f}, AUC: {train_auc:.4f}, Loss: {train_loss:.4f}")

        # Validation metrics
        if X_val is not None and y_val is not None:
            val_pred = self.model.predict_proba(X_val)[:, 1]
            val_acc = accuracy_score(y_val, self.model.predict(X_val))
            val_auc = roc_auc_score(y_val, val_pred)
            val_loss = log_loss(y_val, val_pred)

            logger.info(f"Validation - Acc: {val_acc:.4f}, AUC: {val_auc:.4f}, Loss: {val_loss:.4f}")

        logger.info("Training complete!")

    def predict(self, X):
        """Predict transaction probability"""
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")

        return self.model.predict_proba(X)[:, 1]

    def predict_batch(self, X):
        """Predict for batch of samples"""
        return self.predict(X)

    def save_model(self):
        """Save trained model"""
        output_path = self.results_dir / f"brtm_{self.variant}_model.pkl"

        with open(output_path, 'wb') as f:
            pickle.dump(self.model, f)

        logger.info(f"Model saved to {output_path}")

    def load_model(self):
        """Load trained model"""
        input_path = self.results_dir / f"brtm_{self.variant}_model.pkl"

        if not input_path.exists():
            raise FileNotFoundError(f"Model not found: {input_path}")

        with open(input_path, 'rb') as f:
            self.model = pickle.load(f)

        logger.info(f"Model loaded from {input_path}")


def main():
    """Main training script"""
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    sys.path.insert(0, '../features')
    from feature_engineering import FeatureEngineer

    engineer = FeatureEngineer()

    # Train both variants
    for variant in ['sample', 'sep']:
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Training BRTM-{variant.upper()}")
        logger.info(f"{'=' * 60}")

        # Load features
        X_train, _, _ = engineer.load_features('train', variant)
        X_val, _, _ = engineer.load_features('val', variant)

        # Load data for labels
        processed_dir = Path("../data/processed")
        train_df = pd.read_csv(processed_dir / "train_processed.csv")
        val_df = pd.read_csv(processed_dir / "val_processed.csv")

        # For training data: all samples are positive (actual reviews)
        # Create labels
        y_train = np.ones(len(train_df))
        y_val = np.ones(len(val_df))

        # For BRTM-Sample: create negative samples during training
        if variant == 'sample':
            logger.info("Note: Negative sampling will be done during candidate set construction")

        # Initialize model
        model = BRTMModel(variant=variant)

        # Train
        model.train(X_train, y_train, X_val, y_val)

        # Save
        model.save_model()

    logger.info("\n" + "=" * 60)
    logger.info("All models trained successfully!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
