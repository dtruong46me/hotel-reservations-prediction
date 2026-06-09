"""
hotel_prediction
================
Core ML package for hotel reservation cancellation prediction.

This package is structured in three layers:

Reusable library modules (safe to import anywhere)
---------------------------------------------------
- hotel_prediction.utils.io          — YAML / CSV I/O helpers
- hotel_prediction.utils.ml_params   — scipy distribution builder
- hotel_prediction.exception         — CustomException class
- hotel_prediction.logger            — get_logger() factory

Pipeline components (instantiate and call .run())
-------------------------------------------------
- hotel_prediction.components.data_ingestion   — DataIngestion
- hotel_prediction.components.data_preprocessing — DataPreprocessor
- hotel_prediction.components.model_trainer    — ModelTrainer

Orchestrators (call once per training run)
------------------------------------------
- hotel_prediction.pipelines.training_pipeline — run_training_pipeline()
"""

__version__: str = "1.0.0"
__author__: str = "Hotel Prediction Team"

__all__: list[str] = ["__version__", "__author__"]
