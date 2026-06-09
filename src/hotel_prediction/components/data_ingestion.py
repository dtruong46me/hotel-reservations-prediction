"""Data ingestion component — downloads raw data from GCS and splits into train/test."""

import os
from pathlib import Path

import pandas as pd
from google.cloud import storage
from sklearn.model_selection import train_test_split

from hotel_prediction.exception import CustomException
from hotel_prediction.logger import get_logger
from hotel_prediction.utils.io import read_yaml

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Paths (resolved relative to project root)
# ---------------------------------------------------------------------------
RAW_DIR = Path("artifacts/raw")
RAW_FILE_PATH = RAW_DIR / "raw.csv"
TRAIN_FILE_PATH = RAW_DIR / "train.csv"
TEST_FILE_PATH = RAW_DIR / "test.csv"

CONFIG_PATH = Path("config/config.yaml")


class DataIngestion:
    """Downloads the dataset from Google Cloud Storage and produces train/test splits."""

    def __init__(self, config: dict):
        ingestion_cfg = config["data_ingestion"]
        self.bucket_name: str = ingestion_cfg["bucket_name"]
        self.file_name: str = ingestion_cfg["bucket_file_name"]
        self.train_ratio: float = ingestion_cfg["train_ratio"]

        RAW_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(
            f"DataIngestion initialised — bucket: '{self.bucket_name}', file: '{self.file_name}'"
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _download_from_gcs(self) -> None:
        """Download the raw CSV from GCS to the local raw directory."""
        try:
            client = storage.Client()
            bucket = client.bucket(self.bucket_name)
            blob = bucket.blob(self.file_name)
            blob.download_to_filename(str(RAW_FILE_PATH))
            logger.info(f"Raw file downloaded to {RAW_FILE_PATH}")
        except Exception as e:
            logger.error("Failed to download raw file from GCS")
            raise CustomException("Failed to download CSV from GCS", e)

    def _split_data(self) -> None:
        """Split the raw CSV into train and test sets and persist them."""
        try:
            logger.info("Splitting raw data into train / test sets")
            data = pd.read_csv(RAW_FILE_PATH)
            train_df, test_df = train_test_split(
                data,
                test_size=1 - self.train_ratio,
                random_state=42,
            )
            train_df.to_csv(TRAIN_FILE_PATH, index=False)
            test_df.to_csv(TEST_FILE_PATH, index=False)
            logger.info(
                f"Split complete — train: {len(train_df)} rows, test: {len(test_df)} rows"
            )
        except Exception as e:
            logger.error("Failed to split data")
            raise CustomException("Failed to split data into train/test sets", e)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Execute the full ingestion pipeline."""
        try:
            logger.info("=== Data Ingestion started ===")
            self._download_from_gcs()
            self._split_data()
            logger.info("=== Data Ingestion completed ===")
        except CustomException:
            raise
        except Exception as e:
            raise CustomException("Unexpected error during data ingestion", e)


# ---------------------------------------------------------------------------
# Stand-alone execution
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    config = read_yaml(CONFIG_PATH)
    DataIngestion(config).run()
