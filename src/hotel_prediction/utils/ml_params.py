"""
hotel_prediction.utils.ml_params
=================================
Scipy distribution builder for hyperparameter search configuration.

This module converts the human-readable distribution specs defined in
``config/model_params.yaml`` into the scipy frozen-distribution objects
expected by :class:`sklearn.model_selection.RandomizedSearchCV`.

It has **no I/O side-effects** and no dependency on the rest of the
package — it is a pure transformation utility.

Reusable
--------
build_param_distributions : Convert a YAML param config dict into scipy
                             distribution objects.

Supported distribution types
-----------------------------
+------------+---------------------------+------------------------------+
| YAML type  | scipy equivalent          | Required YAML keys           |
+============+===========================+==============================+
| ``randint``| ``scipy.stats.randint``   | ``low``, ``high``            |
+------------+---------------------------+------------------------------+
| ``uniform``| ``scipy.stats.uniform``   | ``loc``, ``scale``           |
+------------+---------------------------+------------------------------+
| *(list)*   | passed through as-is      | — plain YAML list            |
+------------+---------------------------+------------------------------+

Example
-------
::

    from hotel_prediction.utils.ml_params import build_param_distributions

    raw = {
        "n_estimators": {"type": "randint", "low": 100, "high": 500},
        "learning_rate": {"type": "uniform", "loc": 0.01, "scale": 0.2},
        "boosting_type": ["gbdt", "dart"],
    }
    dists = build_param_distributions(raw)
    # dists["n_estimators"]  → scipy.stats._distn_infrastructure.rv_frozen
    # dists["boosting_type"] → ["gbdt", "dart"]
"""

from __future__ import annotations

from typing import Any

from scipy.stats import randint, uniform

__all__: list[str] = ["build_param_distributions"]

# ── CONSTANTS ─────────────────────────────────────────────────────────────────

# Maps the string ``type`` key from YAML to the corresponding scipy
# distribution factory. Extend this dict to support new distributions
# without changing ``build_param_distributions``.
_DISTRIBUTION_REGISTRY: dict[str, Any] = {
    "randint": randint,
    "uniform": uniform,
}


# ── REUSABLE API ──────────────────────────────────────────────────────────────


def build_param_distributions(
    param_config: dict[str, Any],
) -> dict[str, Any]:
    """Convert a YAML parameter config into scipy distribution objects.

    Iterates over ``param_config`` and for each entry:

    * If the value is a :class:`dict` with a ``"type"`` key → look up the
      scipy factory in :data:`_DISTRIBUTION_REGISTRY`, instantiate it with
      the remaining keys as keyword arguments, and store the frozen
      distribution.
    * Otherwise (plain list or scalar) → pass the value through unchanged.

    Args:
        param_config: Mapping of hyperparameter names to either a
                      distribution spec dict (``{type: ..., **kwargs}``)
                      or a plain list / scalar value. Typically obtained
                      from ``config["lightgbm"]["param_distributions"]``
                      after calling :func:`~hotel_prediction.utils.io.read_yaml`.

    Returns:
        A dict suitable for passing directly to
        :class:`sklearn.model_selection.RandomizedSearchCV` as its
        ``param_distributions`` argument.

    Raises:
        ValueError: When a distribution spec contains an unknown ``"type"``
                    string not present in :data:`_DISTRIBUTION_REGISTRY`.

    Example:
        ::

            raw_config = {
                "n_estimators": {"type": "randint", "low": 100, "high": 500},
                "boosting_type": ["gbdt", "dart", "goss"],
            }
            dists = build_param_distributions(raw_config)
            # Pass to RandomizedSearchCV:
            search = RandomizedSearchCV(model, param_distributions=dists, ...)
    """
    result: dict[str, Any] = {}

    for param_name, spec in param_config.items():
        if isinstance(spec, dict) and "type" in spec:
            dist_type: str = spec["type"]
            if dist_type not in _DISTRIBUTION_REGISTRY:
                supported = sorted(_DISTRIBUTION_REGISTRY)
                raise ValueError(
                    f"Unknown distribution type '{dist_type}' for parameter "
                    f"'{param_name}'. Supported types: {supported}"
                )
            kwargs: dict[str, Any] = {k: v for k, v in spec.items() if k != "type"}
            result[param_name] = _DISTRIBUTION_REGISTRY[dist_type](**kwargs)
        else:
            # Plain list or scalar — pass through unchanged.
            result[param_name] = spec

    return result
