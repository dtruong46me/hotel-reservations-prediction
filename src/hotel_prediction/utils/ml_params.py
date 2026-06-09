"""ML parameter utilities — parse YAML-defined scipy distributions for hyperparameter search."""

from typing import Any

from scipy.stats import randint, uniform

_DISTRIBUTION_MAP = {
    "randint": randint,
    "uniform": uniform,
}


def build_param_distributions(param_config: dict) -> dict[str, Any]:
    """
    Parse the param_distributions section from model_params.yaml and
    convert distribution specs into scipy distribution objects.

    Supported YAML formats:
        # scipy distribution:
        n_estimators: {type: randint, low: 100, high: 500}
        learning_rate: {type: uniform, loc: 0.01, scale: 0.2}

        # plain list (passed through as-is):
        boosting_type: [gbdt, dart, goss]

    Raises:
        ValueError: if a distribution type is not in the supported map.
    """
    result: dict[str, Any] = {}
    for param_name, spec in param_config.items():
        if isinstance(spec, dict) and "type" in spec:
            dist_type = spec["type"]
            if dist_type not in _DISTRIBUTION_MAP:
                raise ValueError(
                    f"Unknown distribution type '{dist_type}' for param '{param_name}'. "
                    f"Supported: {sorted(_DISTRIBUTION_MAP)}"
                )
            kwargs = {k: v for k, v in spec.items() if k != "type"}
            result[param_name] = _DISTRIBUTION_MAP[dist_type](**kwargs)
        else:
            result[param_name] = spec  # list or scalar — pass through
    return result
