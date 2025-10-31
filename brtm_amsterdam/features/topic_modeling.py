#!/usr/bin/env python3
"""
Topic modeling for BRTM
- Implements shared and private topic modeling
- Extracts topic features for listings and user-listing pairs
"""
import os
import sys
import yaml
import logging
import pandas as pd
import numpy as np
from pathlib import Path
import pickle
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.decomposition import LatentDirichletAllocation
import warnings
warnings.filterwarnings('ignore')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class BRTMTopicModeler:
    """
    BRTM Topic Modeling

    Implements two variants:
    1. BRTM-Sample: Shared topics across D, A, B corpora
    2. BRTM-SEP: Separate topics for each corpus (no sharing)
    """

    def __init__(self, config_path="../configs/config.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.n_shared_topics = self.config['features']['topics']['shared_topics']
        self.n_desc_topics = self.config['features']['topics']['description_specific']
        self.n_guest_topics = self.config['features']['topics']['guest_review_specific']
        self.n_host_topics = self.config['features']['topics']['host_review_specific']

        self.alpha = self.config['features']['lda']['alpha']
        self.eta = self.config['features']['lda']['eta']
        self.iterations = self.config['features']['lda']['iterations']
        self.random_state = self.config['features']['lda']['random_state']

        self.cache_dir = Path(self.config['system']['cache_dir'])
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.vectorizers = {}
        self.lda_models = {}

    def create_vectorizer(self, max_features=5000, min_df=2, max_df=0.95):
        """Create count vectorizer for LDA"""
        vectorizer = CountVectorizer(
            max_features=max_features,
            min_df=min_df,
            max_df=max_df,
            stop_words='english',
            token_pattern=r'\b[a-z]{3,}\b',  # Words with at least 3 letters
            lowercase=True
        )
        return vectorizer

    def fit_lda(self, corpus, n_topics, name):
        """Fit LDA model on corpus"""
        logger.info(f"Fitting LDA for {name} with {n_topics} topics...")

        # Vectorize
        vectorizer = self.create_vectorizer()
        doc_term_matrix = vectorizer.fit_transform(corpus)

        logger.info(f"  Vocabulary size: {len(vectorizer.get_feature_names_out())}")
        logger.info(f"  Document-term matrix shape: {doc_term_matrix.shape}")

        # Fit LDA
        lda = LatentDirichletAllocation(
            n_components=n_topics,
            doc_topic_prior=self.alpha,
            topic_word_prior=self.eta,
            max_iter=self.iterations,
            learning_method='batch',
            random_state=self.random_state,
            n_jobs=-1,
            verbose=0
        )

        lda.fit(doc_term_matrix)

        logger.info(f"  LDA fitted. Perplexity: {lda.perplexity(doc_term_matrix):.2f}")

        # Save
        self.vectorizers[name] = vectorizer
        self.lda_models[name] = lda

        return vectorizer, lda

    def transform_corpus(self, corpus, vectorizer, lda):
        """Transform corpus to topic distributions"""
        doc_term_matrix = vectorizer.transform(corpus)
        topic_dist = lda.transform(doc_term_matrix)
        return topic_dist

    def fit_brtm_sample(self, descriptions, guest_reviews, host_reviews):
        """
        Fit BRTM with shared topics (BRTM-Sample variant)

        Strategy: Combine all corpora and fit shared topics,
        then fit corpus-specific topics on residuals
        """
        logger.info("=" * 60)
        logger.info("Fitting BRTM-Sample (shared topics)")
        logger.info("=" * 60)

        # 1. Fit shared topics on combined corpus
        combined_corpus = descriptions + guest_reviews + host_reviews
        logger.info(f"Combined corpus size: {len(combined_corpus)}")

        vec_shared, lda_shared = self.fit_lda(
            combined_corpus,
            self.n_shared_topics,
            'shared'
        )

        # 2. Fit corpus-specific topics
        # For simplicity, we fit separate LDAs
        # In a full implementation, you'd model residuals

        vec_desc, lda_desc = self.fit_lda(
            descriptions,
            self.n_desc_topics,
            'description_specific'
        )

        vec_guest, lda_guest = self.fit_lda(
            guest_reviews,
            self.n_guest_topics,
            'guest_specific'
        )

        if len(host_reviews) > 0:
            vec_host, lda_host = self.fit_lda(
                host_reviews,
                self.n_host_topics,
                'host_specific'
            )
        else:
            logger.warning("No host reviews available. Skipping host-specific topics.")
            vec_host, lda_host = None, None

        logger.info("BRTM-Sample training complete!")

        return {
            'shared': (vec_shared, lda_shared),
            'description': (vec_desc, lda_desc),
            'guest': (vec_guest, lda_guest),
            'host': (vec_host, lda_host)
        }

    def fit_brtm_sep(self, descriptions, guest_reviews, host_reviews):
        """
        Fit BRTM with separate topics (BRTM-SEP variant)

        Each corpus gets its own independent topic space
        """
        logger.info("=" * 60)
        logger.info("Fitting BRTM-SEP (separate topics)")
        logger.info("=" * 60)

        # Fit independent topic models
        vec_desc, lda_desc = self.fit_lda(
            descriptions,
            self.n_shared_topics + self.n_desc_topics,  # Total topics for descriptions
            'description_sep'
        )

        vec_guest, lda_guest = self.fit_lda(
            guest_reviews,
            self.n_shared_topics + self.n_guest_topics,
            'guest_sep'
        )

        if len(host_reviews) > 0:
            vec_host, lda_host = self.fit_lda(
                host_reviews,
                self.n_shared_topics + self.n_host_topics,
                'host_sep'
            )
        else:
            logger.warning("No host reviews available. Skipping host topics.")
            vec_host, lda_host = None, None

        logger.info("BRTM-SEP training complete!")

        return {
            'description': (vec_desc, lda_desc),
            'guest': (vec_guest, lda_guest),
            'host': (vec_host, lda_host)
        }

    def extract_features(self, df, models, variant='sample'):
        """
        Extract topic features from data

        Returns feature matrix for each user-listing-review triple
        """
        logger.info(f"Extracting features for {variant} variant...")

        features_list = []

        if variant == 'sample':
            # Shared + specific features
            # Description features
            desc_shared = self.transform_corpus(
                df['full_description'].fillna('').tolist(),
                models['shared'][0],
                models['shared'][1]
            )

            desc_specific = self.transform_corpus(
                df['full_description'].fillna('').tolist(),
                models['description'][0],
                models['description'][1]
            )

            # Guest review features
            guest_shared = self.transform_corpus(
                df['comments_clean'].fillna('').tolist(),
                models['shared'][0],
                models['shared'][1]
            )

            guest_specific = self.transform_corpus(
                df['comments_clean'].fillna('').tolist(),
                models['guest'][0],
                models['guest'][1]
            )

            # Combine
            features = np.hstack([
                desc_shared,
                desc_specific,
                guest_shared,
                guest_specific
            ])

            # Host features (if available)
            if models['host'][0] is not None:
                host_shared = self.transform_corpus(
                    df['host_response_clean'].fillna('').tolist(),
                    models['shared'][0],
                    models['shared'][1]
                )

                host_specific = self.transform_corpus(
                    df['host_response_clean'].fillna('').tolist(),
                    models['host'][0],
                    models['host'][1]
                )

                features = np.hstack([features, host_shared, host_specific])

        else:  # SEP variant
            # Separate independent features
            desc_features = self.transform_corpus(
                df['full_description'].fillna('').tolist(),
                models['description'][0],
                models['description'][1]
            )

            guest_features = self.transform_corpus(
                df['comments_clean'].fillna('').tolist(),
                models['guest'][0],
                models['guest'][1]
            )

            features = np.hstack([desc_features, guest_features])

            if models['host'][0] is not None:
                host_features = self.transform_corpus(
                    df['host_response_clean'].fillna('').tolist(),
                    models['host'][0],
                    models['host'][1]
                )
                features = np.hstack([features, host_features])

        logger.info(f"Feature matrix shape: {features.shape}")
        return features

    def save_models(self, models, variant):
        """Save trained models"""
        output_path = self.cache_dir / f"topic_models_{variant}.pkl"

        with open(output_path, 'wb') as f:
            pickle.dump(models, f)

        logger.info(f"Models saved to {output_path}")

    def load_models(self, variant):
        """Load trained models"""
        input_path = self.cache_dir / f"topic_models_{variant}.pkl"

        if not input_path.exists():
            raise FileNotFoundError(f"Models not found: {input_path}")

        with open(input_path, 'rb') as f:
            models = pickle.load(f)

        logger.info(f"Models loaded from {input_path}")
        return models


def main():
    """Main execution"""
    import os
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    modeler = BRTMTopicModeler()

    # Load processed data
    processed_dir = Path("../data/processed")
    train_df = pd.read_csv(processed_dir / "train_processed.csv")

    logger.info(f"Loaded {len(train_df)} training samples")

    # Prepare corpora
    descriptions = train_df['full_description'].fillna('').tolist()
    guest_reviews = train_df['comments_clean'].fillna('').tolist()
    host_reviews = train_df['host_response_clean'].fillna('').tolist()

    # Remove empty texts
    descriptions = [d for d in descriptions if len(d) > 10]
    guest_reviews = [g for g in guest_reviews if len(g) > 10]
    host_reviews = [h for h in host_reviews if len(h) > 10]

    logger.info(f"Corpus sizes:")
    logger.info(f"  Descriptions: {len(descriptions)}")
    logger.info(f"  Guest reviews: {len(guest_reviews)}")
    logger.info(f"  Host reviews: {len(host_reviews)}")

    # Fit BRTM-Sample
    models_sample = modeler.fit_brtm_sample(descriptions, guest_reviews, host_reviews)
    modeler.save_models(models_sample, 'sample')

    # Fit BRTM-SEP
    models_sep = modeler.fit_brtm_sep(descriptions, guest_reviews, host_reviews)
    modeler.save_models(models_sep, 'sep')

    logger.info("Topic modeling complete!")


if __name__ == "__main__":
    main()
