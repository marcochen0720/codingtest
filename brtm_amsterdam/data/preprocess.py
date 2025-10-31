#!/usr/bin/env python3
"""
Data preprocessing and cleaning for BRTM
- Text cleaning
- Deduplication (especially for host responses)
- Time-based splitting
- Sample construction
"""
import os
import sys
import yaml
import logging
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import re
from collections import defaultdict
import hashlib

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DataPreprocessor:
    """Preprocess and clean Airbnb data for BRTM"""

    def __init__(self, config_path="../configs/config.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.raw_dir = Path("./raw")
        self.processed_dir = Path("./processed")
        self.processed_dir.mkdir(parents=True, exist_ok=True)

        self.min_desc_length = self.config['data']['min_description_length']
        self.min_review_length = self.config['data']['min_review_length']
        self.dedup_threshold = self.config['data']['dedup']['similarity_threshold']

        self.random_state = self.config['system']['random_seed']
        np.random.seed(self.random_state)

    def clean_text(self, text):
        """Clean and normalize text"""
        if pd.isna(text) or not isinstance(text, str):
            return ""

        # Convert to lowercase
        text = text.lower()

        # Remove URLs
        text = re.sub(r'http\S+|www.\S+', '', text)

        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)

        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        # Remove very short texts
        if len(text) < 10:
            return ""

        return text

    def detect_language(self, text):
        """
        Simple language detection
        For production, use langdetect or fasttext
        """
        # Simple heuristic: check for English common words
        english_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'is', 'was', 'are', 'were'}

        if not text:
            return 'unknown'

        words = set(text.lower().split())
        english_count = len(words & english_words)

        if english_count >= 2:
            return 'en'
        else:
            return 'other'

    def deduplicate_texts(self, texts, method='minhash'):
        """
        Deduplicate similar texts using MinHash or simple similarity

        For production, use datasketch library for MinHash/SimHash
        Here we use a simplified approach
        """
        logger.info(f"Deduplicating {len(texts)} texts using {method}")

        unique_texts = []
        seen_hashes = set()

        for text in texts:
            if not text or len(text) < self.min_review_length:
                continue

            # Simple hash-based deduplication
            # For similar texts, use normalized hash
            normalized = re.sub(r'[^a-z\s]', '', text.lower())
            normalized = re.sub(r'\s+', ' ', normalized).strip()

            # Create hash
            text_hash = hashlib.md5(normalized.encode()).hexdigest()

            if text_hash not in seen_hashes:
                seen_hashes.add(text_hash)
                unique_texts.append(text)

        logger.info(f"After deduplication: {len(unique_texts)} unique texts ({len(texts) - len(unique_texts)} removed)")

        return unique_texts

    def load_and_merge_data(self):
        """Load and merge listings, reviews, and host responses"""
        logger.info("Loading data files...")

        # Load listings
        listing_files = list(self.raw_dir.glob("listings_*.csv*"))
        if not listing_files:
            raise FileNotFoundError("No listing files found")

        listings_df = pd.read_csv(listing_files[0], compression='infer' if listing_files[0].suffix == '.gz' else None)
        logger.info(f"Loaded {len(listings_df)} listings")

        # Load guest reviews
        review_files = list(self.raw_dir.glob("reviews_*.csv*"))
        if not review_files:
            raise FileNotFoundError("No review files found")

        reviews_df = pd.read_csv(review_files[0], compression='infer' if review_files[0].suffix == '.gz' else None)
        logger.info(f"Loaded {len(reviews_df)} guest reviews")

        # Load host responses
        host_response_file = Path("./crawled/host_responses.csv")
        if host_response_file.exists():
            host_responses_df = pd.read_csv(host_response_file)
            logger.info(f"Loaded {len(host_responses_df)} host responses")
        else:
            logger.warning("No host responses found. Creating empty dataframe.")
            host_responses_df = pd.DataFrame(columns=['listing_id', 'review_id', 'host_response'])

        # Load calendar (for availability)
        calendar_files = list(self.raw_dir.glob("calendar_*.csv*"))
        if calendar_files:
            calendar_df = pd.read_csv(calendar_files[0], compression='infer' if calendar_files[0].suffix == '.gz' else None)
            logger.info(f"Loaded {len(calendar_df)} calendar entries")
        else:
            logger.warning("No calendar file found")
            calendar_df = None

        return listings_df, reviews_df, host_responses_df, calendar_df

    def clean_listings(self, listings_df):
        """Clean and process listings data"""
        logger.info("Cleaning listings...")

        # Clean text fields
        if 'description' in listings_df.columns:
            listings_df['description_clean'] = listings_df['description'].apply(self.clean_text)
        else:
            listings_df['description_clean'] = ""

        if 'neighborhood_overview' in listings_df.columns:
            listings_df['neighborhood_overview_clean'] = listings_df['neighborhood_overview'].apply(self.clean_text)
        else:
            listings_df['neighborhood_overview_clean'] = ""

        # Combine description fields
        listings_df['full_description'] = (
            listings_df['description_clean'] + " " +
            listings_df['neighborhood_overview_clean']
        ).str.strip()

        # Filter by description length
        before = len(listings_df)
        listings_df = listings_df[listings_df['full_description'].str.len() >= self.min_desc_length]
        logger.info(f"Filtered listings by description length: {before} -> {len(listings_df)}")

        # Parse price (remove $ and commas)
        if 'price' in listings_df.columns:
            listings_df['price_numeric'] = listings_df['price'].astype(str).str.replace('$', '').str.replace(',', '').astype(float)
        else:
            listings_df['price_numeric'] = 100.0

        # Parse boolean fields
        for col in ['instant_bookable', 'host_is_superhost']:
            if col in listings_df.columns:
                listings_df[f'{col}_bool'] = listings_df[col].astype(str).str.lower().isin(['t', 'true', '1'])

        # Extract numeric features
        numeric_features = ['accommodates', 'bedrooms', 'beds', 'number_of_reviews', 'review_scores_rating']
        for col in numeric_features:
            if col in listings_df.columns:
                listings_df[col] = pd.to_numeric(listings_df[col], errors='coerce').fillna(0)

        logger.info(f"Cleaned {len(listings_df)} listings")
        return listings_df

    def clean_reviews(self, reviews_df):
        """Clean and process reviews"""
        logger.info("Cleaning guest reviews...")

        # Parse dates
        reviews_df['date'] = pd.to_datetime(reviews_df['date'], errors='coerce')
        reviews_df = reviews_df.dropna(subset=['date'])

        # Clean comments
        reviews_df['comments_clean'] = reviews_df['comments'].apply(self.clean_text)

        # Filter by length
        before = len(reviews_df)
        reviews_df = reviews_df[reviews_df['comments_clean'].str.len() >= self.min_review_length]
        logger.info(f"Filtered reviews by length: {before} -> {len(reviews_df)}")

        # Detect language (optional: filter English only)
        reviews_df['language'] = reviews_df['comments_clean'].apply(self.detect_language)

        logger.info(f"Cleaned {len(reviews_df)} reviews")
        return reviews_df

    def clean_host_responses(self, host_responses_df):
        """Clean and deduplicate host responses"""
        logger.info("Cleaning host responses...")

        if len(host_responses_df) == 0:
            logger.warning("No host responses to clean")
            return host_responses_df

        # Clean text
        host_responses_df['host_response_clean'] = host_responses_df['host_response'].apply(self.clean_text)

        # Filter by length
        before = len(host_responses_df)
        host_responses_df = host_responses_df[host_responses_df['host_response_clean'].str.len() >= self.min_review_length]
        logger.info(f"Filtered host responses by length: {before} -> {len(host_responses_df)}")

        # Deduplicate (important for template-like host responses)
        unique_responses = self.deduplicate_texts(host_responses_df['host_response_clean'].tolist())

        # Keep only unique responses
        host_responses_df = host_responses_df[host_responses_df['host_response_clean'].isin(unique_responses)]

        logger.info(f"After deduplication: {len(host_responses_df)} unique host responses")
        return host_responses_df

    def create_time_splits(self, reviews_df):
        """
        Create train/val/test splits based on time

        Following paper: 12 months total (8 train + 1 val + 3 test)
        """
        logger.info("Creating time-based splits...")

        # Get date range
        min_date = reviews_df['date'].min()
        max_date = reviews_df['date'].max()

        logger.info(f"Data date range: {min_date} to {max_date}")

        # Find a 12-month window with sufficient data
        # Try to use most recent 12 months
        end_date = max_date
        start_date = end_date - timedelta(days=365)

        # Filter to this window
        window_reviews = reviews_df[(reviews_df['date'] >= start_date) & (reviews_df['date'] <= end_date)]

        if len(window_reviews) < 100:
            logger.warning(f"Insufficient data in 12-month window. Using all available data.")
            window_reviews = reviews_df
            start_date = min_date
            end_date = max_date

        # Calculate split dates
        train_end = start_date + timedelta(days=8 * 30)  # 8 months
        val_end = train_end + timedelta(days=30)  # 1 month
        test_end = end_date  # Remaining 3 months

        # Create splits
        train_df = window_reviews[window_reviews['date'] < train_end]
        val_df = window_reviews[(window_reviews['date'] >= train_end) & (window_reviews['date'] < val_end)]
        test_df = window_reviews[(window_reviews['date'] >= val_end) & (window_reviews['date'] <= test_end)]

        logger.info(f"Split summary:")
        logger.info(f"  Train: {len(train_df)} reviews ({start_date.date()} to {train_end.date()})")
        logger.info(f"  Val:   {len(val_df)} reviews ({train_end.date()} to {val_end.date()})")
        logger.info(f"  Test:  {len(test_df)} reviews ({val_end.date()} to {test_end.date()})")

        return {
            'train': train_df,
            'val': val_df,
            'test': test_df,
            'dates': {
                'start': start_date,
                'train_end': train_end,
                'val_end': val_end,
                'test_end': test_end
            }
        }

    def merge_and_save(self, listings_df, reviews_df, host_responses_df, splits):
        """Merge data and save processed files"""
        logger.info("Merging data...")

        # Merge reviews with host responses
        reviews_merged = reviews_df.merge(
            host_responses_df[['review_id', 'host_response_clean']],
            left_on='id',
            right_on='review_id',
            how='left'
        )

        reviews_merged['has_host_response'] = reviews_merged['host_response_clean'].notna()

        logger.info(f"Reviews with host responses: {reviews_merged['has_host_response'].sum()} / {len(reviews_merged)}")

        # Save processed listings
        output_listings = self.processed_dir / "listings_processed.csv"
        listings_df.to_csv(output_listings, index=False)
        logger.info(f"Saved processed listings to {output_listings}")

        # Save split reviews
        for split_name, split_df in splits.items():
            if split_name == 'dates':
                continue

            # Merge with listings
            split_merged = split_df.merge(
                reviews_merged[['id', 'listing_id', 'date', 'reviewer_id', 'comments_clean', 'host_response_clean', 'has_host_response']],
                left_on='id',
                right_on='id',
                how='left'
            )

            # Merge with listing info
            split_merged = split_merged.merge(
                listings_df[['id', 'host_id', 'full_description', 'price_numeric', 'accommodates',
                            'number_of_reviews', 'neighbourhood_cleansed', 'room_type',
                            'instant_bookable_bool']],
                left_on='listing_id',
                right_on='id',
                how='left',
                suffixes=('', '_listing')
            )

            output_file = self.processed_dir / f"{split_name}_processed.csv"
            split_merged.to_csv(output_file, index=False)
            logger.info(f"Saved {split_name} split to {output_file}")

        # Save split dates
        import json
        dates_dict = {k: v.isoformat() for k, v in splits['dates'].items()}
        with open(self.processed_dir / "split_dates.json", 'w') as f:
            json.dump(dates_dict, f, indent=2)

        logger.info("Data preprocessing complete!")


def main():
    """Main execution"""
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    preprocessor = DataPreprocessor()

    # Load data
    listings_df, reviews_df, host_responses_df, calendar_df = preprocessor.load_and_merge_data()

    # Clean data
    listings_df = preprocessor.clean_listings(listings_df)
    reviews_df = preprocessor.clean_reviews(reviews_df)
    host_responses_df = preprocessor.clean_host_responses(host_responses_df)

    # Create time splits
    splits = preprocessor.create_time_splits(reviews_df)

    # Merge and save
    preprocessor.merge_and_save(listings_df, reviews_df, host_responses_df, splits)

    logger.info("All preprocessing complete!")


if __name__ == "__main__":
    main()
