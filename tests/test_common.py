"""Tests for hotel_prediction.utils.common"""

import os
import tempfile

import pandas as pd
import pytest
import yaml

from hotel_prediction.utils.io import load_data, read_yaml
from hotel_prediction.utils.ml_params import build_param_distributions



# ---------------------------------------------------------------------------
# read_yaml
# ---------------------------------------------------------------------------

def test_read_yaml_returns_dict(tmp_path):
    config_file = tmp_path / "test.yaml"
    config_file.write_text("key: value\nnested:\n  a: 1\n")
    result = read_yaml(config_file)
    assert result == {"key": "value", "nested": {"a": 1}}


def test_read_yaml_missing_file_raises():
    with pytest.raises(Exception):
        read_yaml("/nonexistent/path/config.yaml")


# ---------------------------------------------------------------------------
# load_data
# ---------------------------------------------------------------------------

def test_load_data_returns_dataframe(tmp_path):
    csv_file = tmp_path / "test.csv"
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    df.to_csv(csv_file, index=False)

    result = load_data(csv_file)
    assert isinstance(result, pd.DataFrame)
    assert list(result.columns) == ["a", "b"]
    assert len(result) == 2


def test_load_data_missing_file_raises():
    with pytest.raises(Exception):
        load_data("/nonexistent/data.csv")


# ---------------------------------------------------------------------------
# build_param_distributions
# ---------------------------------------------------------------------------

def test_build_param_distributions_randint():
    config = {"n_estimators": {"type": "randint", "low": 10, "high": 100}}
    result = build_param_distributions(config)
    # Should be a scipy frozen distribution
    assert hasattr(result["n_estimators"], "rvs")


def test_build_param_distributions_uniform():
    config = {"learning_rate": {"type": "uniform", "loc": 0.01, "scale": 0.2}}
    result = build_param_distributions(config)
    assert hasattr(result["learning_rate"], "rvs")


def test_build_param_distributions_list_passthrough():
    config = {"boosting_type": ["gbdt", "dart"]}
    result = build_param_distributions(config)
    assert result["boosting_type"] == ["gbdt", "dart"]


def test_build_param_distributions_unknown_type_raises():
    config = {"param": {"type": "unknown_dist", "a": 1}}
    with pytest.raises(ValueError, match="Unknown distribution type"):
        build_param_distributions(config)
