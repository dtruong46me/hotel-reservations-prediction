"""Data preprocessing component — encodes, balances, and selects features."""

from pathlib import Path

import numpy as np
import pandas as pd
from imblearn.over_sampling import SMOTE
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder

from hotel_prediction.exception import CustomException
from hotel_prediction.logger import get_logger
from hotel_prediction.utils.io import load_data, read_yaml

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
RAW_DIR = Path("artifacts/raw")
TRAIN_FILE_PATH = RAW_DIR / "train.csv"
TEST_FILE_PATH = RAW_DIR / "test.csv"

PROCESSED_DIR = Path("artifacts/processed")
PROCESSED_TRAIN_PATH = PROCESSED_DIR / "processed_train.csv"
PROCESSED_TEST_PATH = PROCESSED_DIR / "processed_test.csv"

CONFIG_PATH = Path("config/config.yaml")

TARGET_COLUMN = "booking_status"
COLUMNS_TO_DROP = ["Unnamed: 0", "Booking_ID"]


class DataPreprocessor:
    """Applies encoding, imbalance correction, and feature selection to the dataset."""

    def __init__(
        self,
        train_path: Path,
        test_path: Path,
        processed_dir: Path,
        config_path: Path,
    ):
        self.train_path = Path(train_path)
        self.test_path = Path(test_path)
        self.processed_dir = Path(processed_dir)
        self.config = read_yaml(config_path)["data_processing"]

        self.processed_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _encode_and_clean(self, df: pd.DataFrame) -> pd.DataFrame:
        """Drop unused columns, deduplicate, label-encode categoricals, fix skew."""
        try:
            logger.info("Dropping unused columns and duplicates")
            existing_drop = [c for c in COLUMNS_TO_DROP if c in df.columns]
            df = df.drop(columns=existing_drop).drop_duplicates()

            # Label encoding
            cat_cols: list[str] = self.config["categorical_columns"]
            num_cols: list[str] = self.config["numerical_columns"]
            encoder = LabelEncoder()
            mappings: dict = {}

            for col in cat_cols:
                if col in df.columns:
                    df[col] = encoder.fit_transform(df[col])
                    mappings[col] = dict(
                        zip(encoder.classes_, encoder.transform(encoder.classes_))
                    )

            logger.info(f"Label mappings: {mappings}")

            # Skewness correction (log1p)
            skew_threshold: float = self.config["skewness_threshold"]
            skewed_cols = (
                df[num_cols]
                .apply(lambda x: x.skew())
                .pipe(lambda s: s[s > skew_threshold].index.tolist())
            )
            if skewed_cols:
                logger.info(f"Applying log1p to skewed columns: {skewed_cols}")
                df[skewed_cols] = np.log1p(df[skewed_cols])

            return df
        except Exception as e:
            logger.error(f"Error during encode/clean step: {e}")
            raise CustomException("Failed during encoding and cleaning", e)

    def _balance(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply SMOTE to address class imbalance."""
        try:
            logger.info("Applying SMOTE for class balancing")
            X = df.drop(columns=[TARGET_COLUMN])
            y = df[TARGET_COLUMN]
            X_res, y_res = SMOTE(random_state=42).fit_resample(X, y)
            balanced = pd.DataFrame(X_res, columns=X.columns)
            balanced[TARGET_COLUMN] = y_res
            logger.info(
                f"Balanced dataset — class distribution: {balanced[TARGET_COLUMN].value_counts().to_dict()}"
            )
            return balanced
        except Exception as e:
            logger.error(f"Error during balancing step: {e}")
            raise CustomException("Failed during data balancing", e)

    def _select_features(self, df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
        """Use RandomForest importance to select top-N features."""
        try:
            n_features: int = self.config["no_of_features"]
            logger.info(f"Selecting top {n_features} features via RandomForest importance")
            X = df.drop(columns=[TARGET_COLUMN])
            y = df[TARGET_COLUMN]

            rf = RandomForestClassifier(random_state=42)
            rf.fit(X, y)

            importance_df = (
                pd.DataFrame({"feature": X.columns, "importance": rf.feature_importances_})
                .sort_values("importance", ascending=False)
            )
            top_features = importance_df["feature"].head(n_features).tolist()
            logger.info(f"Selected features: {top_features}")

            return df[top_features + [TARGET_COLUMN]], top_features
        except Exception as e:
            logger.error(f"Error during feature selection: {e}")
            raise CustomException("Failed during feature selection", e)

    def _save(self, df: pd.DataFrame, path: Path) -> None:
        """Persist a DataFrame to CSV."""
        try:
            df.to_csv(path, index=False)
            logger.info(f"Saved {len(df)} rows to {path}")
        except Exception as e:
            logger.error(f"Error saving data to {path}: {e}")
            raise CustomException("Failed to save processed data", e)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Execute the full preprocessing pipeline."""
        try:
            logger.info("=== Data Preprocessing started ===")

            train_df = load_data(self.train_path)
            test_df = load_data(self.test_path)

            train_df = self._encode_and_clean(train_df)
            test_df = self._encode_and_clean(test_df)

            train_df = self._balance(train_df)
            test_df = self._balance(test_df)

            train_df, selected_features = self._select_features(train_df)
            # Apply same feature set to test (+ target)
            test_df = test_df[selected_features + [TARGET_COLUMN]]

            self._save(train_df, PROCESSED_TRAIN_PATH)
            self._save(test_df, PROCESSED_TEST_PATH)

            logger.info("=== Data Preprocessing completed ===")

        except CustomException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in preprocessing pipeline: {e}")
            raise CustomException("Unexpected error during preprocessing pipeline", e)


# ---------------------------------------------------------------------------
# Stand-alone execution
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    DataPreprocessor(
        TRAIN_FILE_PATH, TEST_FILE_PATH, PROCESSED_DIR, CONFIG_PATH
    ).run()
