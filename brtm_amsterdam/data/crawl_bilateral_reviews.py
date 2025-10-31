#!/usr/bin/env python3
"""
Crawl bilateral reviews (Host -> Guest reviews) from Airbnb
Note: This is a placeholder implementation. Actual implementation needs:
1. Respect robots.txt and ToS
2. Rate limiting
3. Proper authentication if required
4. Legal compliance for web scraping
"""
import os
import sys
import time
import json
import yaml
import logging
import requests
from pathlib import Path
import pandas as pd
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import random

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class BilateralReviewCrawler:
    """
    Crawler for Host -> Guest reviews (bilateral reviews)

    WARNING: This is a simplified implementation for demonstration.
    Real implementation must:
    - Respect robots.txt
    - Follow rate limits
    - Handle authentication
    - Comply with Terms of Service
    """

    def __init__(self, config_path="../configs/config.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.rate_limit = self.config['crawling']['rate_limit']
        self.max_retries = self.config['crawling']['max_retries']
        self.timeout = self.config['crawling']['timeout']
        self.user_agent = self.config['crawling']['user_agent']

        self.crawled_dir = Path("./crawled")
        self.crawled_dir.mkdir(parents=True, exist_ok=True)

        self.session = requests.Session()
        self.session.headers.update({'User-Agent': self.user_agent})

    def check_robots_txt(self, base_url):
        """Check if crawling is allowed by robots.txt"""
        try:
            robots_url = urljoin(base_url, '/robots.txt')
            response = self.session.get(robots_url, timeout=10)

            if response.status_code == 200:
                logger.info("robots.txt retrieved successfully")
                # Simple check - in production use robotparser
                if "User-agent: *" in response.text and "Disallow: /" in response.text:
                    logger.warning("robots.txt disallows crawling")
                    return False
            return True

        except Exception as e:
            logger.warning(f"Could not check robots.txt: {e}")
            return False

    def crawl_review_page(self, listing_id, review_id):
        """
        Attempt to crawl host's response to a guest review

        Note: Airbnb's structure may vary. This is illustrative.
        Real implementation needs to handle:
        - Authentication
        - Dynamic content loading
        - API endpoints
        """
        url = f"https://www.airbnb.com/rooms/{listing_id}"

        try:
            time.sleep(self.rate_limit)  # Rate limiting

            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # This is a placeholder - actual selectors depend on Airbnb's HTML structure
            host_responses = []

            # In reality, host responses might be in a different endpoint or require API access
            # This is a simplified mock
            review_containers = soup.find_all('div', class_='review-container')

            for container in review_containers:
                host_response = container.find('div', class_='host-response')
                if host_response:
                    host_responses.append({
                        'listing_id': listing_id,
                        'review_id': review_id,
                        'host_response': host_response.get_text(strip=True),
                        'crawled_at': pd.Timestamp.now()
                    })

            return host_responses

        except Exception as e:
            logger.error(f"Error crawling listing {listing_id}: {e}")
            return []

    def generate_mock_host_reviews(self, reviews_df):
        """
        Generate mock host-to-guest reviews for testing

        In production, this would be replaced with actual crawling
        """
        logger.warning("Generating mock host-to-guest reviews for testing")

        host_responses = []

        # Sample ~30% of reviews to have host responses (realistic proportion)
        sampled_reviews = reviews_df.sample(frac=0.3, random_state=42)

        templates = [
            "Thank you {} for being a great guest! We hope to host you again soon.",
            "It was a pleasure hosting {}! Very respectful and clean guest.",
            "{} was a wonderful guest. Highly recommend to other hosts!",
            "Thanks {} for staying with us. You are welcome anytime!",
            "Great communication with {}. Left the place in perfect condition.",
            "{} was an excellent guest. Would definitely host again!",
            "We enjoyed hosting {}. Very friendly and respectful.",
            "Thank you {} for choosing our place. Hope you enjoyed Amsterdam!",
            "{} was a fantastic guest. Easy to communicate with and very tidy.",
            "It was great to host {}. Respectful of house rules and neighbors.",
        ]

        for idx, review in sampled_reviews.iterrows():
            template = random.choice(templates)
            reviewer_name = review.get('reviewer_name', 'our guest')

            host_response = template.format(reviewer_name)

            # Add some variation
            if random.random() > 0.7:
                host_response += " We hope you had a great time exploring the city."

            host_responses.append({
                'listing_id': review['listing_id'],
                'review_id': review['id'],
                'reviewer_id': review['reviewer_id'],
                'host_response': host_response,
                'response_date': review['date'] + pd.Timedelta(days=random.randint(1, 7)),
                'response_length': len(host_response)
            })

        host_reviews_df = pd.DataFrame(host_responses)

        logger.info(f"Generated {len(host_reviews_df)} host responses")
        return host_reviews_df

    def crawl_all_reviews(self, reviews_csv_path):
        """
        Main crawling function

        For demonstration, this generates mock data.
        Replace with actual crawling logic for production.
        """
        logger.info(f"Loading reviews from {reviews_csv_path}")
        reviews_df = pd.read_csv(reviews_csv_path)

        logger.info(f"Found {len(reviews_df)} guest reviews")

        # Check robots.txt (currently disabled for mock data)
        # if not self.check_robots_txt("https://www.airbnb.com"):
        #     logger.error("Crawling not allowed by robots.txt")
        #     logger.info("Falling back to mock data generation")

        # Generate mock host reviews
        host_reviews_df = self.generate_mock_host_reviews(reviews_df)

        # Save to file
        output_path = self.crawled_dir / "host_responses.csv"
        host_reviews_df.to_csv(output_path, index=False)

        logger.info(f"Saved host responses to {output_path}")
        return host_reviews_df


def main():
    """Main execution"""
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    crawler = BilateralReviewCrawler()

    # Find review files
    raw_dir = Path("./raw")
    review_files = list(raw_dir.glob("reviews_*.csv*"))

    if not review_files:
        logger.error("No review files found. Run download_insideairbnb.py first.")
        sys.exit(1)

    # Use the first (or most recent) review file
    review_file = review_files[0]
    logger.info(f"Using review file: {review_file}")

    # Crawl bilateral reviews
    host_reviews_df = crawler.crawl_all_reviews(review_file)

    logger.info(f"Crawling complete! Found {len(host_reviews_df)} host responses")


if __name__ == "__main__":
    main()
