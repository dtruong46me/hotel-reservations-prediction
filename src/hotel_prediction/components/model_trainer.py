"""Model training component — hyperparameter tuning, evaluation, and MLflow logging."""

import os
from pathlib import Path
from typing import Any

import joblib
import lightgbm as lgb
import mlflow
import mlflow.sklearn
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import RandomizedSearchCV

from hotel_prediction.exception import CustomException
from hotel_prediction.logger import get_logger
from hotel_prediction.utils.io import load_data, read_yaml
from hotel_prediction.utils.ml_params import build_param_distributions


logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROCESSED_DIR = Path("artifacts/processed")
PROCESSED_TRAIN_PATH = PROCESSED_DIR / "processed_train.csv"
PROCESSED_TEST_PATH = PROCESSED_DIR / "processed_test.csv"

MODEL_DIR = Path("artifacts/models")
MODEL_OUTPUT_PATH = MODEL_DIR / "lgbm_model.pkl"

CONFIG_PATH = Path("config/config.yaml")
MODEL_PARAMS_PATH = Path("config/model_params.yaml")

TARGET_COLUMN = "booking_status"


class ModelTrainer:
    """Trains a LightGBM classifier with randomised hyperparameter search and MLflow tracking."""

    def __init__(
        self,
        train_path: Path,
        test_path: Path,
        model_output_path: Path,
        model_params_path: Path,
    ):
        self.train_path = Path(train_path)
        self.test_path = Path(test_path)
        self.model_output_path = Path(model_output_path)

        params_config = read_yaml(model_params_path)["lightgbm"]
        self.param_distributions = build_param_distributions(
            params_config["param_distributions"]
        )
        self.search_params: dict[str, Any] = params_config["random_search"]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load_data(self) -> tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]:
        try:
            train_df = load_data(self.train_path)
            test_df = load_data(self.test_path)

            X_train = train_df.drop(columns=[TARGET_COLUMN])
            y_train = train_df[TARGET_COLUMN]
            X_test = test_df.drop(columns=[TARGET_COLUMN])
            y_test = test_df[TARGET_COLUMN]

            logger.info(
                f"Data loaded — train: {X_train.shape}, test: {X_test.shape}"
            )
            return X_train, y_train, X_test, y_test
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            raise CustomException("Failed to load training data", e)

    def _tune_and_train(
        self, X_train: pd.DataFrame, y_train: pd.Series
    ) -> lgb.LGBMClassifier:
        try:
            logger.info("Starting hyperparameter tuning with RandomizedSearchCV")
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
            logger.info(f"Best parameters found: {search.best_params_}")
            return best_model
        except Exception as e:
            logger.error(f"Error during hyperparameter tuning: {e}")
            raise CustomException("Failed during model training / tuning", e)

    def _evaluate(
        self, model: lgb.LGBMClassifier, X_test: pd.DataFrame, y_test: pd.Series
    ) -> dict[str, float]:
        try:
            logger.info("Evaluating model on test set")
            y_pred = model.predict(X_test)
            metrics = {
                "accuracy": accuracy_score(y_test, y_pred),
                "precision": precision_score(y_test, y_pred),
                "recall": recall_score(y_test, y_pred),
                "f1": f1_score(y_test, y_pred),
            }
            for name, value in metrics.items():
                logger.info(f"  {name}: {value:.4f}")
            return metrics
        except Exception as e:
            logger.error(f"Error during model evaluation: {e}")
            raise CustomException("Failed during model evaluation", e)

    def _save_model(self, model: lgb.LGBMClassifier) -> None:
        try:
            self.model_output_path.parent.mkdir(parents=True, exist_ok=True)
            joblib.dump(model, self.model_output_path)
            logger.info(f"Model saved to {self.model_output_path}")
        except Exception as e:
            logger.error(f"Error saving model: {e}")
            raise CustomException("Failed to save model", e)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Execute training pipeline with MLflow experiment tracking."""
        try:
            logger.info("=== Model Training started ===")

            with mlflow.start_run():
                mlflow.set_tag("component", "model_trainer")

                # Log datasets
                mlflow.log_artifact(str(self.train_path), artifact_path="datasets")
                mlflow.log_artifact(str(self.test_path), artifact_path="datasets")

                X_train, y_train, X_test, y_test = self._load_data()
                best_model = self._tune_and_train(X_train, y_train)
                metrics = self._evaluate(best_model, X_test, y_test)

                self._save_model(best_model)

                # Log to MLflow
                mlflow.log_params(best_model.get_params())
                mlflow.log_metrics(metrics)
                mlflow.log_artifact(str(self.model_output_path))

                logger.info("=== Model Training completed ===")

        except CustomException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in model training pipeline: {e}")
            raise CustomException("Unexpected error during model training", e)


# ---------------------------------------------------------------------------
# Stand-alone execution
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    ModelTrainer(
        PROCESSED_TRAIN_PATH,
        PROCESSED_TEST_PATH,
        MODEL_OUTPUT_PATH,
        MODEL_PARAMS_PATH,
    ).run()
