#!/usr/bin/env python3
"""
Candidate Set Construction for BRTM Evaluation

For each test transaction, construct a candidate set of 20 listings:
- 1 positive (actual booked listing)
- 19 negatives (available and similar listings)
"""
import os
import sys
import yaml
import logging
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class CandidateSetConstructor:
    """Construct candidate sets for evaluation"""

    def __init__(self, config_path="../configs/config.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.num_candidates = self.config['data']['num_candidates']
        self.similarity_config = self.config['data']['similarity']
        self.random_state = self.config['system']['random_seed']

        np.random.seed(self.random_state)

    def is_similar(self, listing1, listing2):
        """
        Check if two listings are similar based on configured criteria
        """
        # Same neighborhood
        if self.similarity_config['same_neighborhood']:
            if listing1.get('neighbourhood_cleansed') != listing2.get('neighbourhood_cleansed'):
                return False

        # Price tolerance
        price_tol = self.similarity_config['price_tolerance']
        price1 = listing1.get('price_numeric', 100)
        price2 = listing2.get('price_numeric', 100)

        if abs(price1 - price2) / (price1 + 1e-6) > price_tol:
            return False

        # Room type match
        if self.similarity_config['room_type_match']:
            if listing1.get('room_type') != listing2.get('room_type'):
                return False

        # Capacity tolerance
        cap_tol = self.similarity_config['capacity_tolerance']
        cap1 = listing1.get('accommodates', 2)
        cap2 = listing2.get('accommodates', 2)

        if abs(cap1 - cap2) > cap_tol:
            return False

        return True

    def is_available(self, listing, date, calendar_df=None):
        """
        Check if listing was available at given date

        In practice, this would check calendar data
        For now, we use a simplified heuristic
        """
        if calendar_df is None:
            # Assume listings with fewer bookings are more likely available
            # This is a simplification
            return True

        # Check calendar
        listing_calendar = calendar_df[
            (calendar_df['listing_id'] == listing['id']) &
            (calendar_df['date'] == date)
        ]

        if len(listing_calendar) == 0:
            return True  # Assume available if no calendar data

        return listing_calendar['available'].iloc[0] in ['t', 'True', True, 1]

    def sample_negative_candidates(self, positive_listing, all_listings, n_negatives=19, exclude_ids=None):
        """
        Sample negative candidates similar to positive listing
        """
        if exclude_ids is None:
            exclude_ids = set()

        # Filter out the positive listing and already excluded
        candidates = all_listings[
            (~all_listings['id'].isin(exclude_ids)) &
            (all_listings['id'] != positive_listing['id'])
        ].copy()

        if len(candidates) == 0:
            logger.warning("No candidate listings available for negative sampling")
            return pd.DataFrame()

        # Calculate similarity scores
        similarities = []
        for idx, candidate in candidates.iterrows():
            if self.is_similar(positive_listing, candidate):
                # Add some randomness to similarity score
                score = np.random.random()
                similarities.append((idx, score))

        if len(similarities) == 0:
            # If no similar listings found, relax criteria
            logger.debug("No similar listings found, using random sampling")
            similar_candidates = candidates
        else:
            # Sort by similarity score
            similarities.sort(key=lambda x: x[1], reverse=True)
            similar_indices = [s[0] for s in similarities]
            similar_candidates = candidates.loc[similar_indices]

        # Sample n_negatives
        if len(similar_candidates) < n_negatives:
            logger.debug(f"Only {len(similar_candidates)} similar candidates found, expected {n_negatives}")
            n_negatives = len(similar_candidates)

        if n_negatives == 0:
            return pd.DataFrame()

        sampled = similar_candidates.head(n_negatives)

        return sampled

    def construct_candidate_sets(self, test_df, all_listings_df, calendar_df=None):
        """
        Construct candidate sets for all test samples

        Returns:
            List of candidate sets, each containing 20 listings (1 positive + 19 negatives)
        """
        logger.info(f"Constructing candidate sets for {len(test_df)} test samples...")

        candidate_sets = []

        for idx, test_sample in test_df.iterrows():
            # Get positive listing
            positive_listing_id = test_sample['listing_id']
            positive_listing = all_listings_df[all_listings_df['id'] == positive_listing_id]

            if len(positive_listing) == 0:
                logger.warning(f"Positive listing {positive_listing_id} not found in listings database")
                continue

            positive_listing = positive_listing.iloc[0]

            # Sample negative candidates
            negative_candidates = self.sample_negative_candidates(
                positive_listing,
                all_listings_df,
                n_negatives=self.num_candidates - 1,
                exclude_ids={positive_listing_id}
            )

            if len(negative_candidates) < self.num_candidates - 1:
                logger.debug(f"Sample {idx}: Only {len(negative_candidates)} negatives found")

            # Create candidate set
            candidate_set = {
                'test_sample_idx': idx,
                'reviewer_id': test_sample['reviewer_id'],
                'date': test_sample['date'],
                'positive_listing_id': positive_listing_id,
                'candidate_listing_ids': [positive_listing_id] + negative_candidates['id'].tolist(),
                'ground_truth_rank': 0  # Positive is always at rank 0
            }

            candidate_sets.append(candidate_set)

            if (idx + 1) % 100 == 0:
                logger.info(f"  Processed {idx + 1}/{len(test_df)} samples")

        logger.info(f"Constructed {len(candidate_sets)} candidate sets")

        # Save candidate sets
        output_dir = Path("../data/processed")
        output_file = output_dir / "candidate_sets.pkl"

        import pickle
        with open(output_file, 'wb') as f:
            pickle.dump(candidate_sets, f)

        logger.info(f"Candidate sets saved to {output_file}")

        return candidate_sets


def main():
    """Main execution"""
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    constructor = CandidateSetConstructor()

    # Load data
    processed_dir = Path("../data/processed")

    test_df = pd.read_csv(processed_dir / "test_processed.csv")
    listings_df = pd.read_csv(processed_dir / "listings_processed.csv")

    logger.info(f"Loaded {len(test_df)} test samples")
    logger.info(f"Loaded {len(listings_df)} listings")

    # Construct candidate sets
    candidate_sets = constructor.construct_candidate_sets(test_df, listings_df)

    # Print statistics
    avg_candidates = np.mean([len(cs['candidate_listing_ids']) for cs in candidate_sets])
    logger.info(f"\nStatistics:")
    logger.info(f"  Total candidate sets: {len(candidate_sets)}")
    logger.info(f"  Average candidates per set: {avg_candidates:.1f}")


if __name__ == "__main__":
    main()
