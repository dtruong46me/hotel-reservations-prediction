"""
hotel_prediction.utils
======================
Utility sub-package containing pure, reusable helper modules.

Sub-modules
-----------
io
    File I/O — YAML reading and CSV loading.
    No side-effects beyond the I/O operation itself.

ml_params
    Scipy distribution builder for hyperparameter search.
    Completely stateless; no I/O, no logging.

Convenience re-exports
----------------------
The three most commonly used symbols are re-exported here so callers
can use the short form::

    from hotel_prediction.utils import read_yaml, load_data, build_param_distributions

instead of the longer module-qualified form.  Both import styles work.
"""

from __future__ import annotations

import os
import sys

__root__ = os.getcwd()
sys.path.insert(0, __root__)

from src.hotel_prediction.utils.io import load_data, read_yaml
from src.hotel_prediction.utils.ml_params import build_param_distributions

__all__: list[str] = [
    "read_yaml",
    "load_data",
    "build_param_distributions",
]
