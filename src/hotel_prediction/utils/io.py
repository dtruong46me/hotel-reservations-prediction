"""
hotel_prediction.utils.io
=========================
File I/O helpers — YAML configuration reading and CSV data loading.

All functions in this module are **pure utilities**: they have no
side-effects beyond the I/O operation they describe and are safe to
import and call from any context.

Reusable
--------
read_yaml  : Load a YAML file into a plain Python dict.
load_data  : Load a CSV file into a :class:`pandas.DataFrame`.

Example
-------
::

    from hotel_prediction.utils.io import read_yaml, load_data

    config = read_yaml("config/config.yaml")
    df = load_data("artifacts/raw/train.csv")
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

__all__: list[str] = ["read_yaml", "load_data"]
__root__ = os.getcwd()
sys.path.insert(0, __root__)

from src.hotel_prediction.exception import CustomException
from src.hotel_prediction.logger import get_logger

_logger = get_logger(__name__)


# ── REUSABLE API ──────────────────────────────────────────────────────────────


def read_yaml(file_path: str | Path) -> dict[str, Any]:
    """Read a YAML file and return its contents as a plain Python dict.

    Args:
        file_path: Absolute or relative path to the ``.yaml`` / ``.yml``
                   file. Both :class:`str` and :class:`pathlib.Path` are
                   accepted.

    Returns:
        The deserialised YAML document as a nested ``dict``.

    Raises:
        CustomException: Wraps :class:`FileNotFoundError` when the path
                         does not exist, or any YAML parse error.

    Example:
        ::

            config = read_yaml("config/config.yaml")
            bucket = config["data_ingestion"]["bucket_name"]
    """
    path = Path(file_path)
    try:
        if not path.exists():
            raise FileNotFoundError(f"YAML file not found: {path}")
        with path.open("r", encoding="utf-8") as fh:
            content: dict[str, Any] = yaml.safe_load(fh)
        _logger.info("Loaded YAML: %s", path)
        return content
    except Exception as exc:
        _logger.error("Failed to read YAML file: %s", path)
        raise CustomException("Failed to read YAML file", exc)


def load_data(path: str | Path) -> pd.DataFrame:
    """Load a CSV file into a :class:`pandas.DataFrame`.

    Args:
        path: Absolute or relative path to the CSV file. Both
              :class:`str` and :class:`pathlib.Path` are accepted.

    Returns:
        A :class:`pandas.DataFrame` containing all rows and columns
        from the CSV file.

    Raises:
        CustomException: Wraps any :mod:`pandas` read error (file not
                         found, parse error, encoding issue, etc.).

    Example:
        ::

            df = load_data("artifacts/raw/train.csv")
            print(df.shape)   # (n_rows, n_cols)
    """
    csv_path = Path(path)
    try:
        df: pd.DataFrame = pd.read_csv(csv_path)
        _logger.info("Loaded CSV: %s  shape=%s", csv_path, df.shape)
        return df
    except Exception as exc:
        _logger.error("Failed to load CSV: %s", csv_path)
        raise CustomException("Failed to load data", exc)
