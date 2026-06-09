"""
hotel_prediction.pipelines.training_pipeline
============================================
End-to-end orchestration of the ML training workflow.

This module acts as the entry point for executing the entire machine
learning pipeline in sequence. It wires together the three core
components:

1. :class:`~hotel_prediction.components.data_ingestion.DataIngestion`
   (Downloads data and splits it).
2. :class:`~hotel_prediction.components.data_preprocessing.DataPreprocessor`
   (Cleans, encodes, balances, and selects features).
3. :class:`~hotel_prediction.components.model_trainer.ModelTrainer`
   (Tunes hyperparameters, trains, evaluates, and logs to MLflow).

Reusable
--------
run_training_pipeline : Execute the full pipeline programmatically.

Entry point (run once to trigger the full pipeline)
----------------------------------------------------
::

    python -m hotel_prediction.pipelines.training_pipeline
"""

from __future__ import annotations

import os
import sys

__root__ = os.getcwd()
sys.path.insert(0, __root__)

from src.hotel_prediction.components.data_ingestion import (
    CONFIG_PATH,
    DataIngestion,
)
from src.hotel_prediction.components.data_preprocessing import (
    PROCESSED_DIR,
    PROCESSED_TEST_PATH,
    PROCESSED_TRAIN_PATH,
    TEST_FILE_PATH,
    TRAIN_FILE_PATH,
    DataPreprocessor,
)
from src.hotel_prediction.components.model_trainer import (
    MODEL_OUTPUT_PATH,
    MODEL_PARAMS_PATH,
    ModelTrainer,
)
from src.hotel_prediction.logger import get_logger
from src.hotel_prediction.utils.io import read_yaml

__all__: list[str] = ["run_training_pipeline"]

_logger = get_logger(__name__)


# ── REUSABLE API ──────────────────────────────────────────────────────────────


def run_training_pipeline() -> None:
    """Execute the full end-to-end training pipeline.

    This function coordinates the execution of the three main components
    in the correct sequence, passing default file paths configured in each
    component module.

    Raises:
        CustomException: If any component in the pipeline fails.
    """
    _logger.info("========== Training Pipeline started ==========")

    # 1. Data Ingestion
    _logger.info("--- Step 1: Data Ingestion ---")
    config: dict = read_yaml(CONFIG_PATH)
    DataIngestion(config).run()

    # 2. Data Preprocessing
    _logger.info("--- Step 2: Data Preprocessing ---")
    DataPreprocessor(
        train_path=TRAIN_FILE_PATH,
        test_path=TEST_FILE_PATH,
        processed_dir=PROCESSED_DIR,
        config_path=CONFIG_PATH,
    ).run()

    # 3. Model Training
    _logger.info("--- Step 3: Model Training ---")
    ModelTrainer(
        train_path=PROCESSED_TRAIN_PATH,
        test_path=PROCESSED_TEST_PATH,
        model_output_path=MODEL_OUTPUT_PATH,
        model_params_path=MODEL_PARAMS_PATH,
    ).run()

    _logger.info("========== Training Pipeline completed ==========")


# ── ENTRY POINT (run once per training job) ───────────────────────────────────

if __name__ == "__main__":
    run_training_pipeline()
