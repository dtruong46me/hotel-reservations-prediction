"""I/O utilities — YAML config reading and CSV data loading."""

from pathlib import Path

import pandas as pd
import yaml

from hotel_prediction.exception import CustomException
from hotel_prediction.logger import get_logger

logger = get_logger(__name__)


def read_yaml(file_path: str | Path) -> dict:
    """Read a YAML file and return its contents as a dict."""
    path = Path(file_path)
    try:
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        with path.open("r") as f:
            config = yaml.safe_load(f)
        logger.info(f"Successfully read YAML: {path}")
        return config
    except Exception as e:
        logger.error(f"Error reading YAML file: {path}")
        raise CustomException("Failed to read YAML file", e)


def load_data(path: str | Path) -> pd.DataFrame:
    """Load a CSV file into a DataFrame."""
    try:
        df = pd.read_csv(path)
        logger.info(f"Loaded data from {path} — shape: {df.shape}")
        return df
    except Exception as e:
        logger.error(f"Error loading data from {path}: {e}")
        raise CustomException("Failed to load data", e)
