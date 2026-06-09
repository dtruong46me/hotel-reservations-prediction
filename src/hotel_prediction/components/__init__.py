"""
hotel_prediction.components
============================
Individual pipeline step implementations.

Each module in this sub-package contains exactly one public class that
encapsulates one discrete step of the ML training pipeline.  The classes
are designed to be:

* **Reusable** — instantiate with explicit paths/config and call ``.run()``.
  They carry no implicit global state and can be composed freely.
* **Independently executable** — every module has an ``if __name__ == "__main__"``
  block using the default path constants so the step can be run in
  isolation during development or debugging.

Components
----------
DataIngestion
    Download raw CSV from Google Cloud Storage and split into
    train / test sets.  Writes to ``artifacts/raw/``.

DataPreprocessor
    Label-encode categoricals, correct skewness, apply SMOTE for class
    balancing, and select top-N features via RandomForest importance.
    Writes to ``artifacts/processed/``.

ModelTrainer
    Run randomised hyperparameter search over LightGBM, evaluate on the
    test set, persist the best model, and log everything to MLflow.
    Writes to ``artifacts/models/``.
"""
