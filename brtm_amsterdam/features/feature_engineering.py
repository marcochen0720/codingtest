#!/usr/bin/env python3
"""
Feature engineering for BRTM
- Extract user and listing features
- Combine topic features with metadata features
"""
import os
import sys
import yaml
import logging
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import pickle

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class FeatureEngineer:
    """Engineer features for BRTM prediction"""

    def __init__(self, config_path="../configs/config.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.cache_dir = Path(self.config['system']['cache_dir'])
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def extract_user_features(self, df):
        """Extract user-level features"""
        logger.info("Extracting user features...")

        features = pd.DataFrame()

        # User tenure (days since first review or host_since)
        if 'date' in df.columns:
            features['user_tenure_days'] = (
                pd.to_datetime(df['date']) - pd.to_datetime('2020-01-01')
            ).dt.days.fillna(0)
        else:
            features['user_tenure_days'] = 0

        # Number of reviews (proxy from listing)
        features['user_num_reviews'] = df.get('number_of_reviews', 0).fillna(0)

        # Verification status (from listing's host)
        features['user_is_verified'] = df.get('host_is_superhost', False).fillna(False).astype(int)

        # Superhost status
        features['user_is_superhost'] = df.get('host_is_superhost', False).fillna(False).astype(int)

        # International user (placeholder - would need guest country data)
        features['user_is_international'] = 1  # Default assumption

        logger.info(f"Extracted {features.shape[1]} user features")
        return features

    def extract_listing_features(self, df):
        """Extract listing-level features"""
        logger.info("Extracting listing features...")

        features = pd.DataFrame()

        # Price (normalized)
        price = df.get('price_numeric', 100).fillna(100)
        features['listing_price'] = price
        features['listing_price_log'] = np.log1p(price)

        # Rating
        features['listing_rating'] = df.get('review_scores_rating', 4.5).fillna(4.5) / 5.0  # Normalize to 0-1

        # Number of reviews
        features['listing_num_reviews'] = df.get('number_of_reviews', 0).fillna(0)
        features['listing_num_reviews_log'] = np.log1p(features['listing_num_reviews'])

        # Capacity
        features['listing_accommodates'] = df.get('accommodates', 2).fillna(2)

        # Instant bookable
        features['listing_instant_bookable'] = df.get('instant_bookable_bool', False).fillna(False).astype(int)

        # Room type (one-hot encoding)
        room_type = df.get('room_type', 'Entire home/apt').fillna('Entire home/apt')
        features['listing_room_entire'] = (room_type == 'Entire home/apt').astype(int)
        features['listing_room_private'] = (room_type == 'Private room').astype(int)
        features['listing_room_shared'] = (room_type == 'Shared room').astype(int)

        logger.info(f"Extracted {features.shape[1]} listing features")
        return features

    def extract_interaction_features(self, df):
        """Extract user-listing interaction features"""
        logger.info("Extracting interaction features...")

        features = pd.DataFrame()

        # Price-capacity ratio
        price = df.get('price_numeric', 100).fillna(100)
        capacity = df.get('accommodates', 2).fillna(2).replace(0, 1)
        features['price_per_guest'] = price / capacity

        # Has host response
        features['has_host_response'] = df.get('has_host_response', False).fillna(False).astype(int)

        # Review recency (days between listing reviews and current review)
        # Placeholder - would need temporal data
        features['review_recency'] = 30  # Default

        logger.info(f"Extracted {features.shape[1]} interaction features")
        return features

    def combine_features(self, df, topic_features, variant='sample'):
        """Combine all features into final feature matrix"""
        logger.info(f"Combining features for {variant} variant...")

        # Extract metadata features
        user_features = self.extract_user_features(df)
        listing_features = self.extract_listing_features(df)
        interaction_features = self.extract_interaction_features(df)

        # Combine metadata features
        metadata_features = pd.concat([
            user_features,
            listing_features,
            interaction_features
        ], axis=1)

        # Normalize metadata features
        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler()
        metadata_normalized = scaler.fit_transform(metadata_features)

        # Combine with topic features
        if topic_features is not None:
            combined = np.hstack([topic_features, metadata_normalized])
        else:
            combined = metadata_normalized

        logger.info(f"Final feature shape: {combined.shape}")

        return combined, metadata_features.columns.tolist(), scaler

    def save_features(self, features, feature_names, scaler, split, variant):
        """Save extracted features"""
        output_dir = self.cache_dir / variant
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save features
        np.save(output_dir / f"{split}_features.npy", features)

        # Save feature names
        with open(output_dir / f"{split}_feature_names.pkl", 'wb') as f:
            pickle.dump(feature_names, f)

        # Save scaler
        with open(output_dir / f"{split}_scaler.pkl", 'wb') as f:
            pickle.dump(scaler, f)

        logger.info(f"Features saved to {output_dir}")

    def load_features(self, split, variant):
        """Load saved features"""
        input_dir = self.cache_dir / variant

        features = np.load(input_dir / f"{split}_features.npy")

        with open(input_dir / f"{split}_feature_names.pkl", 'rb') as f:
            feature_names = pickle.load(f)

        with open(input_dir / f"{split}_scaler.pkl", 'rb') as f:
            scaler = pickle.load(f)

        logger.info(f"Features loaded from {input_dir}")
        return features, feature_names, scaler


def main():
    """Main execution"""
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    from topic_modeling import BRTMTopicModeler

    engineer = FeatureEngineer()
    modeler = BRTMTopicModeler()

    # Process for both variants
    for variant in ['sample', 'sep']:
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Processing variant: {variant}")
        logger.info(f"{'=' * 60}")

        # Load topic models
        models = modeler.load_models(variant)

        # Process each split
        for split in ['train', 'val', 'test']:
            logger.info(f"\nProcessing {split} split...")

            # Load data
            processed_dir = Path("../data/processed")
            df = pd.read_csv(processed_dir / f"{split}_processed.csv")

            logger.info(f"Loaded {len(df)} samples")

            # Extract topic features
            topic_features = modeler.extract_features(df, models, variant)

            # Combine with metadata features
            combined_features, feature_names, scaler = engineer.combine_features(
                df, topic_features, variant
            )

            # Save
            engineer.save_features(
                combined_features,
                feature_names,
                scaler,
                split,
                variant
            )

    logger.info("\nFeature engineering complete!")


if __name__ == "__main__":
    main()
