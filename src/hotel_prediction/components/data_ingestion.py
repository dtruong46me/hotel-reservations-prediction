"""
hotel_prediction.components.data_ingestion
==========================================
Download raw dataset from Google Cloud Storage and split into
train / test CSV files.

Reusable
--------
DataIngestion : Configurable ingestion class — instantiate with a config
                dict and call ``.run()``.

Constants (importable by orchestrators)
----------------------------------------
RAW_DIR          : Root directory for raw data artifacts.
RAW_FILE_PATH    : Destination path for the downloaded CSV.
TRAIN_FILE_PATH  : Destination path for the training split.
TEST_FILE_PATH   : Destination path for the test split.
CONFIG_PATH      : Default path to ``config/config.yaml``.

Entry point (run once per ingestion job)
-----------------------------------------
Run this module directly to execute data ingestion as a standalone step::

    python -m hotel_prediction.components.data_ingestion
"""

from __future__ import annotations

import os
import sys

import shutil
from pathlib import Path

import pandas as pd
from google.cloud import storage
from sklearn.model_selection import train_test_split

__root__ = os.getcwd()
sys.path.insert(0, __root__)

from src.hotel_prediction.exception import CustomException
from src.hotel_prediction.logger import get_logger
from src.hotel_prediction.utils.io import read_yaml

__all__: list[str] = [
    "DataIngestion",
    "RAW_DIR",
    "RAW_FILE_PATH",
    "TRAIN_FILE_PATH",
    "TEST_FILE_PATH",
    "CONFIG_PATH",
]

_logger = get_logger(__name__)

# ── CONSTANTS ─────────────────────────────────────────────────────────────────
# Default paths used by the standalone entry point and by the training
# pipeline orchestrator.  Pass different paths to the constructor if you
# want to override these at call-site.

RAW_DIR: Path = Path("artifacts/raw")
RAW_FILE_PATH: Path = RAW_DIR / "raw.csv"
TRAIN_FILE_PATH: Path = RAW_DIR / "train.csv"
TEST_FILE_PATH: Path = RAW_DIR / "test.csv"

CONFIG_PATH: Path = Path("config/config.yaml")


# ── REUSABLE API ──────────────────────────────────────────────────────────────


class DataIngestion:
    """Download the raw dataset from GCS and produce train / test splits.

    This class is **stateless** after construction: calling ``.run()``
    multiple times produces the same result (idempotent, assuming the
    source data in GCS has not changed).

    Attributes:
        bucket_name: Name of the GCS bucket containing the source file.
        file_name: Object name (key) of the CSV file inside the bucket.
        train_ratio: Fraction of rows allocated to the training split
                     (e.g. ``0.8`` → 80 % train, 20 % test).

    Example:
        ::

            from hotel_prediction.utils.io import read_yaml
            from hotel_prediction.components.data_ingestion import (
                DataIngestion,
                CONFIG_PATH,
            )

            config = read_yaml(CONFIG_PATH)
            DataIngestion(config).run()
    """

    def __init__(self, config: dict) -> None:
        """Initialise from the ``data_ingestion`` section of ``config.yaml``.

        Args:
            config: Full application config dict (as returned by
                    :func:`~hotel_prediction.utils.io.read_yaml`).
                    Only the ``"data_ingestion"`` sub-key is consumed.
        """
        ingestion_cfg: dict = config["data_ingestion"]
        self.source_type: str = ingestion_cfg.get("source_type", "gcs")
        self.local_data_path: str = ingestion_cfg.get("local_data_path", "data/Hotel Reservations.csv")
        self.bucket_name: str = ingestion_cfg.get("bucket_name", "")
        self.file_name: str = ingestion_cfg.get("bucket_file_name", "")
        self.train_ratio: float = ingestion_cfg["train_ratio"]

        RAW_DIR.mkdir(parents=True, exist_ok=True)
        _logger.info(
            "DataIngestion ready — source='%s' train_ratio=%.2f",
            self.source_type,
            self.train_ratio,
        )

    # ── Private helpers ───────────────────────────────────────────────────────

    def _get_raw_data(self) -> None:
        """Fetch raw CSV to :data:`RAW_FILE_PATH` based on :attr:`source_type`.

        If source_type is 'local', copies the file from local path.
        If source_type is 'gcs', downloads from GCS.
        """
        if self.source_type == "local":
            self._copy_from_local()
        elif self.source_type == "gcs":
            self._download_from_gcs()
        else:
            raise ValueError(f"Unknown source_type '{self.source_type}'. Use 'local' or 'gcs'.")

    def _copy_from_local(self) -> None:
        """Copy the raw CSV from a local path to :data:`RAW_FILE_PATH`."""
        try:
            local_path = Path(self.local_data_path)
            if not local_path.exists():
                raise FileNotFoundError(f"Local file not found: {local_path}")
            
            _logger.info("Copying local data from '%s'", local_path)
            shutil.copy2(local_path, RAW_FILE_PATH)
            _logger.info("Raw file copied → %s", RAW_FILE_PATH)
        except Exception as exc:
            _logger.error("Local copy failed: %s", exc)
            raise CustomException("Failed to copy local CSV data", exc)

    def _download_from_gcs(self) -> None:
        """Download the raw CSV from GCS to :data:`RAW_FILE_PATH`.

        Uses Application Default Credentials (ADC).  Set the environment
        variable ``GOOGLE_APPLICATION_CREDENTIALS`` to a service-account
        key file if ADC is not configured for your environment.

        Raises:
            CustomException: When the GCS download fails for any reason
                             (permissions, network, missing object, etc.).
        """
        try:
            _logger.info("Connecting to GCS bucket '%s'", self.bucket_name)
            client: storage.Client = storage.Client()
            bucket: storage.Bucket = client.bucket(self.bucket_name)
            blob: storage.Blob = bucket.blob(self.file_name)
            blob.download_to_filename(str(RAW_FILE_PATH))
            _logger.info("Raw file downloaded → %s", RAW_FILE_PATH)
        except Exception as exc:
            _logger.error("GCS download failed: %s", exc)
            raise CustomException("Failed to download CSV from GCS", exc)

    def _split_data(self) -> None:
        """Split the raw CSV into stratified train / test sets.

        Reads :data:`RAW_FILE_PATH`, applies a random split controlled by
        :attr:`train_ratio` (seed fixed at 42 for reproducibility), and
        writes the results to :data:`TRAIN_FILE_PATH` and
        :data:`TEST_FILE_PATH`.

        Raises:
            CustomException: When the CSV cannot be read or written.
        """
        try:
            _logger.info(
                "Splitting raw data (train_ratio=%.2f, random_state=42)",
                self.train_ratio,
            )
            data: pd.DataFrame = pd.read_csv(RAW_FILE_PATH)
            train_df, test_df = train_test_split(
                data,
                test_size=1.0 - self.train_ratio,
                random_state=42,
            )
            train_df.to_csv(TRAIN_FILE_PATH, index=False)
            test_df.to_csv(TEST_FILE_PATH, index=False)
            _logger.info(
                "Split complete — train: %d rows  test: %d rows",
                len(train_df),
                len(test_df),
            )
        except Exception as exc:
            _logger.error("Data split failed: %s", exc)
            raise CustomException("Failed to split data into train/test sets", exc)

    # ── Public API ────────────────────────────────────────────────────────────

    def run(self) -> None:
        """Execute the full ingestion pipeline (fetch → split).

        Steps:
            1. Fetch raw CSV from source (Local/GCS) → ``artifacts/raw/raw.csv``.
            2. Split into train / test → ``artifacts/raw/train.csv``
               and ``artifacts/raw/test.csv``.

        Raises:
            CustomException: Propagated from :meth:`_get_raw_data` or
                             :meth:`_split_data`.
        """
        _logger.info("=== Data Ingestion started ===")
        try:
            self._get_raw_data()
            self._split_data()
        except CustomException:
            raise
        except Exception as exc:
            raise CustomException("Unexpected error during data ingestion", exc)
        _logger.info("=== Data Ingestion completed ===")


# ── ENTRY POINT (run once per ingestion job) ──────────────────────────────────
# Executed only when this module is run directly:
#   python -m hotel_prediction.components.data_ingestion
# Not executed on import.

if __name__ == "__main__":
    DataIngestion(read_yaml(CONFIG_PATH)).run()
