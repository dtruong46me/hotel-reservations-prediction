"""
hotel_prediction.components.model_trainer
==========================================
Hyperparameter tuning, model evaluation, and MLflow experiment logging.

The training step is the **last** stage of the pipeline.  It reads the
processed feature sets produced by
:class:`~hotel_prediction.components.data_preprocessing.DataPreprocessor`,
runs :class:`~sklearn.model_selection.RandomizedSearchCV` over a
:class:`lightgbm.LGBMClassifier`, evaluates the best model on the test
set, persists the model as a ``.pkl`` file, and logs everything to MLflow.

Reusable
--------
ModelTrainer : Configurable trainer class.
evaluate_model : Standalone function — compute classification metrics for
                 any sklearn-compatible model without side-effects.

Constants (importable by orchestrators)
----------------------------------------
PROCESSED_TRAIN_PATH : Default path to the processed training CSV.
PROCESSED_TEST_PATH  : Default path to the processed test CSV.
MODEL_OUTPUT_PATH    : Default destination for the serialised model.
MODEL_PARAMS_PATH    : Default path to ``config/model_params.yaml``.
TARGET_COLUMN        : Name of the label column.

Entry point (run once per training job)
----------------------------------------
::

    python -m hotel_prediction.components.model_trainer
"""

from __future__ import annotations

import os
import sys

from pathlib import Path
from typing import Any

import joblib
import lightgbm as lgb
import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import RandomizedSearchCV

__root__ = os.getcwd()
sys.path.insert(0, __root__)

from src.hotel_prediction.exception import CustomException
from src.hotel_prediction.logger import get_logger
from src.hotel_prediction.utils.io import load_data, read_yaml
from src.hotel_prediction.utils.ml_params import build_param_distributions

__all__: list[str] = [
    "ModelTrainer",
    "evaluate_model",
    "PROCESSED_TRAIN_PATH",
    "PROCESSED_TEST_PATH",
    "MODEL_OUTPUT_PATH",
    "MODEL_PARAMS_PATH",
    "TARGET_COLUMN",
]

_logger = get_logger(__name__)

# ── CONSTANTS ─────────────────────────────────────────────────────────────────

_PROCESSED_DIR: Path = Path("artifacts/processed")
PROCESSED_TRAIN_PATH: Path = _PROCESSED_DIR / "processed_train.csv"
PROCESSED_TEST_PATH: Path = _PROCESSED_DIR / "processed_test.csv"

_MODEL_DIR: Path = Path("artifacts/models")
MODEL_OUTPUT_PATH: Path = _MODEL_DIR / "lgbm_model.pkl"

MODEL_PARAMS_PATH: Path = Path("config/model_params.yaml")

TARGET_COLUMN: str = "booking_status"


# ── REUSABLE API ──────────────────────────────────────────────────────────────


def evaluate_model(
    model: lgb.LGBMClassifier,
    X_test: pd.DataFrame,
    y_test: pd.Series,
) -> dict[str, float]:
    """Compute standard binary-classification metrics for *model* on *X_test*.

    This function is a **pure utility** — it has no side-effects (no
    logging, no file I/O, no MLflow calls) and can be imported and
    reused independently of :class:`ModelTrainer`.

    Args:
        model: A fitted sklearn-compatible classifier exposing a
               ``.predict(X)`` method.
        X_test: Feature matrix for the test set.
        y_test: True binary labels for the test set.

    Returns:
        A dict with the keys ``"accuracy"``, ``"precision"``, ``"recall"``,
        and ``"f1"``, each mapping to a :class:`float` in ``[0, 1]``.

    Raises:
        ValueError: When *y_test* does not contain exactly two distinct
                    classes (binary classification requirement).

    Example:
        ::

            metrics = evaluate_model(fitted_model, X_test, y_test)
            print(f"F1: {metrics['f1']:.4f}")
    """
    y_pred: np.ndarray = model.predict(X_test)
    return {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "precision": float(precision_score(y_test, y_pred)),
        "recall": float(recall_score(y_test, y_pred)),
        "f1": float(f1_score(y_test, y_pred)),
    }


class ModelTrainer:
    """Train a LightGBM classifier with randomised hyperparameter search.

    Workflow inside :meth:`run`:

    1. Load processed train / test CSVs.
    2. Run :class:`~sklearn.model_selection.RandomizedSearchCV` to find
       the best hyperparameter combination.
    3. Evaluate the best model on the test set via :func:`evaluate_model`.
    4. Persist the model to disk with :mod:`joblib`.
    5. Log parameters, metrics, and the model artefact to MLflow.

    Attributes:
        train_path: Path to the processed training CSV.
        test_path: Path to the processed test CSV.
        model_output_path: Destination path for the serialised model.
        param_distributions: Scipy distribution objects for each
                             hyperparameter (built from ``model_params.yaml``).
        search_params: Keyword arguments forwarded to
                       :class:`~sklearn.model_selection.RandomizedSearchCV`
                       (``n_iter``, ``cv``, ``scoring``, etc.).

    Example:
        ::

            from hotel_prediction.components.model_trainer import (
                ModelTrainer,
                PROCESSED_TRAIN_PATH,
                PROCESSED_TEST_PATH,
                MODEL_OUTPUT_PATH,
                MODEL_PARAMS_PATH,
            )

            ModelTrainer(
                train_path=PROCESSED_TRAIN_PATH,
                test_path=PROCESSED_TEST_PATH,
                model_output_path=MODEL_OUTPUT_PATH,
                model_params_path=MODEL_PARAMS_PATH,
            ).run()
    """

    def __init__(
        self,
        train_path: str | Path,
        test_path: str | Path,
        model_output_path: str | Path,
        model_params_path: str | Path,
    ) -> None:
        """Initialise paths and parse hyperparameter distributions.

        Args:
            train_path: Path to ``processed_train.csv``.
            test_path: Path to ``processed_test.csv``.
            model_output_path: Destination for the serialised ``.pkl`` model.
            model_params_path: Path to ``config/model_params.yaml``.
        """
        self.train_path: Path = Path(train_path)
        self.test_path: Path = Path(test_path)
        self.model_output_path: Path = Path(model_output_path)

        lgbm_cfg: dict[str, Any] = read_yaml(model_params_path)["lightgbm"]
        self.param_distributions: dict[str, Any] = build_param_distributions(
            lgbm_cfg["param_distributions"]
        )
        self.search_params: dict[str, Any] = lgbm_cfg["random_search"]

    # ── Private helpers ───────────────────────────────────────────────────────

    def _load_splits(
        self,
    ) -> tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]:
        """Load and split the processed CSVs into feature matrices and labels.

        Returns:
            A 4-tuple ``(X_train, y_train, X_test, y_test)``.

        Raises:
            CustomException: When either CSV cannot be read.
        """
        try:
            train_df: pd.DataFrame = load_data(self.train_path)
            test_df: pd.DataFrame = load_data(self.test_path)

            X_train: pd.DataFrame = train_df.drop(columns=[TARGET_COLUMN])
            y_train: pd.Series = train_df[TARGET_COLUMN]
            X_test: pd.DataFrame = test_df.drop(columns=[TARGET_COLUMN])
            y_test: pd.Series = test_df[TARGET_COLUMN]

            _logger.info(
                "Splits loaded — train: %s  test: %s",
                X_train.shape,
                X_test.shape,
            )
            return X_train, y_train, X_test, y_test
        except Exception as exc:
            _logger.error("Error loading data splits: %s", exc)
            raise CustomException("Failed to load training data", exc)

    def _tune_and_train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
    ) -> lgb.LGBMClassifier:
        """Run RandomizedSearchCV and return the best fitted LGBMClassifier.

        Args:
            X_train: Training feature matrix.
            y_train: Training labels.

        Returns:
            The best :class:`lightgbm.LGBMClassifier` from the search.

        Raises:
            CustomException: Wraps any error raised during fitting.
        """
        try:
            _logger.info(
                "RandomizedSearchCV — n_iter=%d  cv=%d",
                self.search_params["n_iter"],
                self.search_params["cv"],
            )
            base_model = lgb.LGBMClassifier(
                random_state=self.search_params.get("random_state", 42)
            )
            search = RandomizedSearchCV(
                estimator=base_model,
                param_distributions=self.param_distributions,
                n_iter=self.search_params["n_iter"],
                cv=self.search_params["cv"],
                n_jobs=self.search_params.get("n_jobs", -1),
                verbose=self.search_params.get("verbose", 1),
                random_state=self.search_params.get("random_state", 42),
                scoring=self.search_params.get("scoring", "accuracy"),
            )
            search.fit(X_train, y_train)
            best_model: lgb.LGBMClassifier = search.best_estimator_
            _logger.info("Best parameters: %s", search.best_params_)
            return best_model
        except Exception as exc:
            _logger.error("Hyperparameter tuning failed: %s", exc)
            raise CustomException("Failed during model training / tuning", exc)

    def _save_model(self, model: lgb.LGBMClassifier) -> None:
        """Serialise *model* to :attr:`model_output_path` with :mod:`joblib`.

        Creates the parent directory if it does not exist.

        Args:
            model: Fitted classifier to persist.

        Raises:
            CustomException: Wraps any I/O error during serialisation.
        """
        try:
            self.model_output_path.parent.mkdir(parents=True, exist_ok=True)
            joblib.dump(model, self.model_output_path)
            _logger.info("Model saved → %s", self.model_output_path)
        except Exception as exc:
            _logger.error("Error saving model: %s", exc)
            raise CustomException("Failed to save model", exc)

    # ── Public API ────────────────────────────────────────────────────────────

    def run(self) -> None:
        """Execute the full training pipeline under an MLflow run context.

        Steps:
            1. Load train / test splits.
            2. Log dataset artefacts to MLflow.
            3. Tune hyperparameters and fit the best model.
            4. Evaluate on the test set.
            5. Save the model to ``artifacts/models/lgbm_model.pkl``.
            6. Log parameters, metrics, and the model artefact to MLflow.

        Raises:
            CustomException: Propagated from any private helper method.
        """
        _logger.info("=== Model Training started ===")
        try:
            with mlflow.start_run():
                mlflow.set_tag("component", "model_trainer")
                mlflow.log_artifact(str(self.train_path), artifact_path="datasets")
                mlflow.log_artifact(str(self.test_path), artifact_path="datasets")

                X_train, y_train, X_test, y_test = self._load_splits()
                best_model: lgb.LGBMClassifier = self._tune_and_train(X_train, y_train)
                metrics: dict[str, float] = evaluate_model(best_model, X_test, y_test)

                for name, value in metrics.items():
                    _logger.info("  %-12s %.4f", name, value)

                self._save_model(best_model)

                mlflow.log_params(best_model.get_params())
                mlflow.log_metrics(metrics)
                mlflow.log_artifact(str(self.model_output_path))

        except CustomException:
            raise
        except Exception as exc:
            _logger.error("Unexpected error in model training pipeline: %s", exc)
            raise CustomException("Unexpected error during model training", exc)
        _logger.info("=== Model Training completed ===")


# ── ENTRY POINT (run once per training job) ───────────────────────────────────

if __name__ == "__main__":
    ModelTrainer(
        train_path=PROCESSED_TRAIN_PATH,
        test_path=PROCESSED_TEST_PATH,
        model_output_path=MODEL_OUTPUT_PATH,
        model_params_path=MODEL_PARAMS_PATH,
    ).run()
