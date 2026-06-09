"""
hotel_prediction.components.data_preprocessing
===============================================
Transform raw train / test splits into model-ready feature sets.

Processing steps (applied in order inside :meth:`DataPreprocessor.run`):

1. **Clean** — drop housekeeping columns and duplicate rows.
2. **Encode** — label-encode categorical columns; log1p-transform
   heavily skewed numerical columns.
3. **Balance** — oversample the minority class with SMOTE.
4. **Select** — rank all features by RandomForest importance and keep
   the top-N (configured via ``config.yaml``).

Reusable
--------
DataPreprocessor : Configurable preprocessing class.

Constants (importable by orchestrators)
----------------------------------------
TRAIN_FILE_PATH        : Default input path for raw training data.
TEST_FILE_PATH         : Default input path for raw test data.
PROCESSED_DIR          : Root directory for processed outputs.
PROCESSED_TRAIN_PATH   : Default output path for processed training data.
PROCESSED_TEST_PATH    : Default output path for processed test data.
CONFIG_PATH            : Default path to ``config/config.yaml``.
TARGET_COLUMN          : Name of the label column.
COLUMNS_TO_DROP        : Columns always removed before processing.

Entry point (run once per preprocessing job)
---------------------------------------------
::

    python -m hotel_prediction.components.data_preprocessing
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from imblearn.over_sampling import SMOTE
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder

__root__ = os.getcwd()
sys.path.insert(0, __root__)

from src.hotel_prediction.exception import CustomException
from src.hotel_prediction.logger import get_logger
from src.hotel_prediction.utils.io import load_data, read_yaml

__all__: list[str] = [
    "DataPreprocessor",
    "TRAIN_FILE_PATH",
    "TEST_FILE_PATH",
    "PROCESSED_DIR",
    "PROCESSED_TRAIN_PATH",
    "PROCESSED_TEST_PATH",
    "CONFIG_PATH",
    "TARGET_COLUMN",
    "COLUMNS_TO_DROP",
]

_logger = get_logger(__name__)

# ── CONSTANTS ─────────────────────────────────────────────────────────────────

_RAW_DIR: Path = Path("artifacts/raw")
TRAIN_FILE_PATH: Path = _RAW_DIR / "train.csv"
TEST_FILE_PATH: Path = _RAW_DIR / "test.csv"

PROCESSED_DIR: Path = Path("artifacts/processed")
PROCESSED_TRAIN_PATH: Path = PROCESSED_DIR / "processed_train.csv"
PROCESSED_TEST_PATH: Path = PROCESSED_DIR / "processed_test.csv"

CONFIG_PATH: Path = Path("config/config.yaml")

# Domain constant — the prediction target; used throughout the class.
TARGET_COLUMN: str = "booking_status"

# Columns added by pandas indexing or present in the source but carrying
# no predictive value.
COLUMNS_TO_DROP: list[str] = ["Unnamed: 0", "Booking_ID"]


# ── REUSABLE API ──────────────────────────────────────────────────────────────


class DataPreprocessor:
    """Apply encoding, class balancing, and feature selection to raw splits.

    All four transformation steps are exposed as private methods so they
    can be tested in isolation.  The public surface is :meth:`run`, which
    applies them in the correct order and persists the results.

    Attributes:
        train_path: Path to the raw training CSV.
        test_path: Path to the raw test CSV.
        processed_dir: Directory where processed CSVs are written.
        config: The ``"data_processing"`` section of ``config.yaml``.

    Example:
        ::

            from hotel_prediction.components.data_preprocessing import (
                DataPreprocessor,
                TRAIN_FILE_PATH,
                TEST_FILE_PATH,
                PROCESSED_DIR,
                CONFIG_PATH,
            )

            DataPreprocessor(
                train_path=TRAIN_FILE_PATH,
                test_path=TEST_FILE_PATH,
                processed_dir=PROCESSED_DIR,
                config_path=CONFIG_PATH,
            ).run()
    """

    def __init__(
        self,
        train_path: str | Path,
        test_path: str | Path,
        processed_dir: str | Path,
        config_path: str | Path,
    ) -> None:
        """Initialise paths and load the processing config section.

        Args:
            train_path: Path to ``train.csv`` produced by
                        :class:`~hotel_prediction.components.data_ingestion.DataIngestion`.
            test_path: Path to ``test.csv``.
            processed_dir: Directory in which processed CSVs will be saved.
                           Created if it does not exist.
            config_path: Path to ``config/config.yaml``.  Only the
                         ``"data_processing"`` sub-key is consumed.
        """
        self.train_path: Path = Path(train_path)
        self.test_path: Path = Path(test_path)
        self.processed_dir: Path = Path(processed_dir)
        self.config: dict = read_yaml(config_path)["data_processing"]

        self.processed_dir.mkdir(parents=True, exist_ok=True)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _clean_and_encode(self, df: pd.DataFrame) -> pd.DataFrame:
        """Drop junk columns, remove duplicates, encode categoricals, fix skew.

        Applies the following transformations in order:

        1. Drop columns listed in :data:`COLUMNS_TO_DROP` (only those
           that actually exist in *df* to avoid ``KeyError``).
        2. Remove duplicate rows.
        3. Label-encode every column listed under
           ``data_processing.categorical_columns`` in the config.
        4. Apply ``log1p`` to every numerical column whose skewness
           exceeds ``data_processing.skewness_threshold``.

        Args:
            df: Raw split DataFrame (modified in place then returned).

        Returns:
            The cleaned and encoded DataFrame.

        Raises:
            CustomException: Wraps any unexpected error during transformation.
        """
        try:
            existing: list[str] = [c for c in COLUMNS_TO_DROP if c in df.columns]
            df = df.drop(columns=existing).drop_duplicates()
            _logger.info("Cleaned — dropped %d columns, removed duplicates", len(existing))

            cat_cols: list[str] = self.config["categorical_columns"]
            num_cols: list[str] = self.config["numerical_columns"]

            encoder = LabelEncoder()
            mappings: dict[str, dict] = {}
            for col in cat_cols:
                if col in df.columns:
                    df[col] = encoder.fit_transform(df[col])
                    mappings[col] = dict(
                        zip(encoder.classes_, encoder.transform(encoder.classes_))
                    )
            _logger.info("Label mappings: %s", mappings)

            skew_threshold: float = self.config["skewness_threshold"]
            skewed_cols: list[str] = (
                df[num_cols]
                .apply(lambda x: x.skew())
                .pipe(lambda s: s[s > skew_threshold].index.tolist())
            )
            if skewed_cols:
                _logger.info("log1p applied to skewed columns: %s", skewed_cols)
                df[skewed_cols] = np.log1p(df[skewed_cols])

            return df
        except Exception as exc:
            _logger.error("Error during clean/encode step: %s", exc)
            raise CustomException("Failed during encoding and cleaning", exc)

    def _balance(self, df: pd.DataFrame) -> pd.DataFrame:
        """Oversample the minority class with SMOTE.

        Args:
            df: Encoded DataFrame containing :data:`TARGET_COLUMN`.

        Returns:
            A new DataFrame with balanced class distribution.
            Row count will increase; column set is unchanged.

        Raises:
            CustomException: Wraps any SMOTE error.
        """
        try:
            _logger.info("Applying SMOTE (random_state=42)")
            X: pd.DataFrame = df.drop(columns=[TARGET_COLUMN])
            y: pd.Series = df[TARGET_COLUMN]

            X_res, y_res = SMOTE(random_state=42).fit_resample(X, y)

            balanced: pd.DataFrame = pd.DataFrame(X_res, columns=X.columns)
            balanced[TARGET_COLUMN] = y_res

            dist: dict = balanced[TARGET_COLUMN].value_counts().to_dict()
            _logger.info("Balanced class distribution: %s", dist)
            return balanced
        except Exception as exc:
            _logger.error("Error during SMOTE balancing: %s", exc)
            raise CustomException("Failed during data balancing", exc)

    def _select_features(
        self, df: pd.DataFrame
    ) -> tuple[pd.DataFrame, list[str]]:
        """Select top-N features by RandomForest importance.

        Args:
            df: Balanced DataFrame containing :data:`TARGET_COLUMN`.

        Returns:
            A 2-tuple of:

            * The DataFrame reduced to the top-N features plus the target.
            * The ordered list of selected feature names (most important
              first) — callers must apply the same list to the test set
              to ensure consistent column order.

        Raises:
            CustomException: Wraps any RandomForest or pandas error.
        """
        try:
            n_features: int = self.config["no_of_features"]
            _logger.info("Selecting top %d features via RandomForest importance", n_features)

            X: pd.DataFrame = df.drop(columns=[TARGET_COLUMN])
            y: pd.Series = df[TARGET_COLUMN]

            rf = RandomForestClassifier(random_state=42)
            rf.fit(X, y)

            importance_df: pd.DataFrame = (
                pd.DataFrame({"feature": X.columns, "importance": rf.feature_importances_})
                .sort_values("importance", ascending=False)
            )
            top_features: list[str] = importance_df["feature"].head(n_features).tolist()
            _logger.info("Selected features: %s", top_features)

            return df[top_features + [TARGET_COLUMN]], top_features
        except Exception as exc:
            _logger.error("Error during feature selection: %s", exc)
            raise CustomException("Failed during feature selection", exc)

    def _save(self, df: pd.DataFrame, path: Path) -> None:
        """Persist *df* to a CSV file at *path*.

        Args:
            df: DataFrame to save.
            path: Destination file path.  Parent directories must exist.

        Raises:
            CustomException: Wraps any I/O error.
        """
        try:
            df.to_csv(path, index=False)
            _logger.info("Saved %d rows → %s", len(df), path)
        except Exception as exc:
            _logger.error("Error saving data to %s: %s", path, exc)
            raise CustomException("Failed to save processed data", exc)

    # ── Public API ────────────────────────────────────────────────────────────

    def run(self) -> None:
        """Execute the full preprocessing pipeline (clean → balance → select → save).

        Applies all transformation steps to both the training and test sets.
        Feature selection is performed on the training set only; the
        resulting feature list is then applied to the test set to guarantee
        consistent column ordering.

        Writes:
            * ``artifacts/processed/processed_train.csv``
            * ``artifacts/processed/processed_test.csv``

        Raises:
            CustomException: Propagated from any private helper method.
        """
        _logger.info("=== Data Preprocessing started ===")
        try:
            train_df: pd.DataFrame = load_data(self.train_path)
            test_df: pd.DataFrame = load_data(self.test_path)

            train_df = self._clean_and_encode(train_df)
            test_df = self._clean_and_encode(test_df)

            train_df = self._balance(train_df)
            test_df = self._balance(test_df)

            train_df, selected_features = self._select_features(train_df)
            # Align test set to the same feature schema derived from train.
            test_df = test_df[selected_features + [TARGET_COLUMN]]

            self._save(train_df, PROCESSED_TRAIN_PATH)
            self._save(test_df, PROCESSED_TEST_PATH)

        except CustomException:
            raise
        except Exception as exc:
            _logger.error("Unexpected error in preprocessing pipeline: %s", exc)
            raise CustomException("Unexpected error during preprocessing pipeline", exc)
        _logger.info("=== Data Preprocessing completed ===")


# ── ENTRY POINT (run once per preprocessing job) ──────────────────────────────

if __name__ == "__main__":
    DataPreprocessor(
        train_path=TRAIN_FILE_PATH,
        test_path=TEST_FILE_PATH,
        processed_dir=PROCESSED_DIR,
        config_path=CONFIG_PATH,
    ).run()
