"""
app.main
========
Flask application — serves the hotel reservation prediction model.

Reusable
--------
create_app : Application factory — creates and configures the Flask app.

Constants
---------
MODEL_PATH  : Default path to the saved LightGBM model.
CONFIG_PATH : Default path to the configuration YAML file.

Entry point (run development server)
------------------------------------
Run locally (development only)::

    python src/app/main.py

Or via gunicorn (production)::

    gunicorn -b 0.0.0.0:8080 "app.main:create_app()"
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from flask import Flask, render_template, request
from werkzeug.wrappers.response import Response

__all__: list[str] = ["create_app"]
__root__ = os.getcwd()

sys.path.insert(0, __root__)

from src.hotel_prediction.logger import get_logger
from src.hotel_prediction.utils.io import read_yaml

_logger = get_logger(__name__)

# ── CONSTANTS ─────────────────────────────────────────────────────────────────

MODEL_PATH: Path = Path("artifacts/models/lgbm_model.pkl")
CONFIG_PATH: Path = Path("config/config.yaml")


# ── REUSABLE API ──────────────────────────────────────────────────────────────


def create_app() -> Flask:
    """Application factory — creates and configures the Flask app.

    Loads the serialized model from :data:`MODEL_PATH` into memory. The
    model is loaded once when the application starts.

    Returns:
        A configured :class:`flask.Flask` application instance.

    Raises:
        FileNotFoundError: If the model file does not exist at
                           :data:`MODEL_PATH`.
    """
    _here: Path = Path(__file__).parent
    app = Flask(
        __name__,
        template_folder=str(_here / "templates"),
        static_folder=str(_here / "static"),
    )

    # Load model once at startup
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model not found at {MODEL_PATH}. "
            "Run the training pipeline first: "
            "python -m hotel_prediction.pipelines.training_pipeline"
        )
    model = joblib.load(MODEL_PATH)
    _logger.info("Model loaded from %s", MODEL_PATH)

    @app.route("/", methods=["GET", "POST"])
    def index() -> str:
        """Handle the main index route, displaying form and predictions."""
        prediction: int | None = None
        error: str | None = None

        if request.method == "POST":
            try:
                # Extract form fields and convert to required types
                lead_time = int(request.form["lead_time"])
                no_of_special_requests = int(request.form["no_of_special_requests"])
                avg_price_per_room = float(request.form["avg_price_per_room"])
                arrival_month = int(request.form["arrival_month"])
                arrival_date = int(request.form["arrival_date"])
                market_segment_type = int(request.form["market_segment_type"])
                no_of_week_nights = int(request.form["no_of_week_nights"])
                no_of_weekend_nights = int(request.form["no_of_weekend_nights"])
                type_of_meal_plan = int(request.form["type_of_meal_plan"])
                room_type_reserved = int(request.form["room_type_reserved"])

                # Create feature array matching the model's expected shape (1, 10)
                features: np.ndarray = np.array(
                    [
                        [
                            lead_time,
                            no_of_special_requests,
                            avg_price_per_room,
                            arrival_month,
                            arrival_date,
                            market_segment_type,
                            no_of_week_nights,
                            no_of_weekend_nights,
                            type_of_meal_plan,
                            room_type_reserved,
                        ]
                    ]
                )

                prediction = int(model.predict(features)[0])
                _logger.info(
                    "Prediction: %d for input features: %s",
                    prediction,
                    features.tolist(),
                )

            except (ValueError, KeyError) as exc:
                error = f"Invalid input: {exc}"
                _logger.warning("Bad input from user: %s", exc)

        return render_template("index.html", prediction=prediction, error=error)

    @app.route("/health")
    def health() -> tuple[dict[str, str], int]:
        """Simple health-check endpoint.

        Returns:
            A JSON response with status and loaded model path.
        """
        return {"status": "ok", "model": str(MODEL_PATH)}, 200

    return app


# ── ENTRY POINT (run development server) ──────────────────────────────────────

if __name__ == "__main__":
    cfg: dict[str, Any] = read_yaml(CONFIG_PATH).get("app", {})
    host: str = os.getenv("APP_HOST", cfg.get("host", "0.0.0.0"))
    port: int = int(os.getenv("APP_PORT", cfg.get("port", 8080)))
    debug: bool = (
        os.getenv("FLASK_DEBUG", str(cfg.get("debug", False))).lower() == "true"
    )

    flask_app: Flask = create_app()
    flask_app.run(host=host, port=port, debug=debug)
