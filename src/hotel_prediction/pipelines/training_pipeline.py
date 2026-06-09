"""
Training pipeline — orchestrates the full ML workflow:
  1. Data Ingestion  (download from GCS + train/test split)
  2. Data Preprocessing  (encode, balance, feature select)
  3. Model Training  (hyperparameter tuning + MLflow logging)

Usage:
    python -m hotel_prediction.pipelines.training_pipeline
"""

from pathlib import Path

from hotel_prediction.components.data_ingestion import (
    CONFIG_PATH,
    DataIngestion,
)
from hotel_prediction.components.data_preprocessing import (
    PROCESSED_DIR,
    PROCESSED_TEST_PATH,
    PROCESSED_TRAIN_PATH,
    TEST_FILE_PATH,
    TRAIN_FILE_PATH,
    DataPreprocessor,
)
from hotel_prediction.components.model_trainer import (
    MODEL_OUTPUT_PATH,
    MODEL_PARAMS_PATH,
    ModelTrainer,
)
from hotel_prediction.logger import get_logger
from hotel_prediction.utils.io import read_yaml

logger = get_logger(__name__)


def run_training_pipeline() -> None:
    """Execute the full end-to-end training pipeline."""
    logger.info("========== Training Pipeline started ==========")

    # 1. Data Ingestion
    logger.info("--- Step 1: Data Ingestion ---")
    config = read_yaml(CONFIG_PATH)
    DataIngestion(config).run()

    # 2. Data Preprocessing
    logger.info("--- Step 2: Data Preprocessing ---")
    DataPreprocessor(
        train_path=TRAIN_FILE_PATH,
        test_path=TEST_FILE_PATH,
        processed_dir=PROCESSED_DIR,
        config_path=CONFIG_PATH,
    ).run()

    # 3. Model Training
    logger.info("--- Step 3: Model Training ---")
    ModelTrainer(
        train_path=PROCESSED_TRAIN_PATH,
        test_path=PROCESSED_TEST_PATH,
        model_output_path=MODEL_OUTPUT_PATH,
        model_params_path=MODEL_PARAMS_PATH,
    ).run()

    logger.info("========== Training Pipeline completed ==========")


if __name__ == "__main__":
    run_training_pipeline()
