#!/usr/bin/env python3
"""
Download data from Inside Airbnb for Amsterdam
"""
import os
import sys
import requests
import yaml
from pathlib import Path
from datetime import datetime, timedelta
import logging
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class InsideAirbnbDownloader:
    """Download listings, calendar, and reviews from Inside Airbnb"""

    def __init__(self, config_path="../configs/config.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.city = self.config['data']['city']
        self.base_url = self.config['data']['insideairbnb_base']
        self.raw_dir = Path("./raw")
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    def get_available_dates(self):
        """
        Get available data dates from Inside Airbnb
        For Amsterdam, typically quarterly snapshots
        """
        # Common snapshot dates (update based on actual availability)
        # Check: http://insideairbnb.com/get-the-data/
        dates = [
            "2023-03-06",
            "2023-06-05",
            "2023-09-03",
            "2023-12-06"
        ]
        return dates

    def download_file(self, url, output_path, max_retries=3):
        """Download file with retry logic"""
        for attempt in range(max_retries):
            try:
                logger.info(f"Downloading {url} (attempt {attempt + 1}/{max_retries})")
                response = requests.get(url, timeout=60)
                response.raise_for_status()

                with open(output_path, 'wb') as f:
                    f.write(response.content)

                logger.info(f"Successfully downloaded to {output_path}")
                return True

            except Exception as e:
                logger.warning(f"Download failed: {e}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed to download {url} after {max_retries} attempts")
                    return False

    def download_listings(self, date):
        """Download listings.csv.gz for a specific date"""
        url = f"{self.base_url}/{date}/data/listings.csv.gz"
        output = self.raw_dir / f"listings_{date}.csv.gz"

        if output.exists():
            logger.info(f"File already exists: {output}")
            return True

        return self.download_file(url, output)

    def download_reviews(self, date):
        """Download reviews.csv.gz for a specific date"""
        url = f"{self.base_url}/{date}/data/reviews.csv.gz"
        output = self.raw_dir / f"reviews_{date}.csv.gz"

        if output.exists():
            logger.info(f"File already exists: {output}")
            return True

        return self.download_file(url, output)

    def download_calendar(self, date):
        """Download calendar.csv.gz for a specific date"""
        url = f"{self.base_url}/{date}/data/calendar.csv.gz"
        output = self.raw_dir / f"calendar_{date}.csv.gz"

        if output.exists():
            logger.info(f"File already exists: {output}")
            return True

        return self.download_file(url, output)

    def download_all(self):
        """Download all required data files"""
        dates = self.get_available_dates()
        logger.info(f"Downloading data for {len(dates)} dates: {dates}")

        success_count = 0
        for date in dates:
            logger.info(f"\n{'=' * 60}")
            logger.info(f"Processing date: {date}")
            logger.info(f"{'=' * 60}")

            success = True
            success &= self.download_listings(date)
            success &= self.download_reviews(date)
            success &= self.download_calendar(date)

            if success:
                success_count += 1

        logger.info(f"\n{'=' * 60}")
        logger.info(f"Download complete: {success_count}/{len(dates)} dates successful")
        logger.info(f"{'=' * 60}")

        return success_count == len(dates)

    def create_sample_data(self):
        """
        Create sample data files for testing when actual download fails
        This is a fallback for development/testing
        """
        logger.warning("Creating sample data files for testing purposes")

        import pandas as pd
        import numpy as np

        # Create sample listings
        n_listings = 1000
        listings_df = pd.DataFrame({
            'id': range(1, n_listings + 1),
            'name': [f'Listing {i}' for i in range(1, n_listings + 1)],
            'description': [f'Beautiful apartment in Amsterdam center. {" ".join(["Great location"] * 10)}' for _ in range(n_listings)],
            'neighborhood_overview': ['Nice neighborhood'] * n_listings,
            'host_id': np.random.randint(1, 500, n_listings),
            'host_name': [f'Host {i}' for i in np.random.randint(1, 500, n_listings)],
            'host_since': ['2020-01-01'] * n_listings,
            'host_is_superhost': np.random.choice(['t', 'f'], n_listings),
            'neighbourhood_cleansed': np.random.choice(['Centrum', 'De Pijp', 'Jordaan', 'Oud-West'], n_listings),
            'latitude': np.random.uniform(52.35, 52.39, n_listings),
            'longitude': np.random.uniform(4.88, 4.92, n_listings),
            'property_type': np.random.choice(['Entire apartment', 'Private room', 'Shared room'], n_listings),
            'room_type': np.random.choice(['Entire home/apt', 'Private room', 'Shared room'], n_listings),
            'accommodates': np.random.randint(1, 6, n_listings),
            'bathrooms': np.random.uniform(1, 3, n_listings),
            'bedrooms': np.random.randint(1, 4, n_listings),
            'beds': np.random.randint(1, 5, n_listings),
            'price': np.random.uniform(50, 300, n_listings),
            'minimum_nights': np.random.randint(1, 7, n_listings),
            'maximum_nights': np.random.randint(30, 365, n_listings),
            'instant_bookable': np.random.choice(['t', 'f'], n_listings),
            'number_of_reviews': np.random.randint(0, 200, n_listings),
            'review_scores_rating': np.random.uniform(4.0, 5.0, n_listings),
        })

        listings_df.to_csv(self.raw_dir / "listings_sample.csv", index=False)

        # Create sample reviews
        n_reviews = 5000
        reviews_df = pd.DataFrame({
            'listing_id': np.random.choice(listings_df['id'], n_reviews),
            'id': range(1, n_reviews + 1),
            'date': pd.date_range('2023-01-01', periods=n_reviews, freq='2H'),
            'reviewer_id': np.random.randint(1, 2000, n_reviews),
            'reviewer_name': [f'Reviewer {i}' for i in np.random.randint(1, 2000, n_reviews)],
            'comments': [
                f'Great place to stay! Very clean and comfortable. The host was very responsive. Would definitely recommend this place to anyone visiting Amsterdam. {"Perfect location. " * 5}'
                for _ in range(n_reviews)
            ]
        })

        reviews_df.to_csv(self.raw_dir / "reviews_sample.csv", index=False)

        # Create sample calendar
        n_calendar = 20000
        calendar_df = pd.DataFrame({
            'listing_id': np.random.choice(listings_df['id'], n_calendar),
            'date': np.tile(pd.date_range('2023-01-01', periods=365), n_calendar // 365),
            'available': np.random.choice(['t', 'f'], n_calendar),
            'price': np.random.uniform(50, 300, n_calendar),
        })

        calendar_df.to_csv(self.raw_dir / "calendar_sample.csv", index=False)

        logger.info("Sample data created successfully")
        return True


def main():
    """Main execution"""
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    downloader = InsideAirbnbDownloader()

    # Try to download real data
    success = downloader.download_all()

    # If download fails, create sample data
    if not success:
        logger.warning("Download failed or incomplete. Creating sample data for testing.")
        downloader.create_sample_data()

    logger.info("Data preparation complete!")


if __name__ == "__main__":
    main()
