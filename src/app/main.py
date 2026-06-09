"""
Flask application — serves the hotel reservation prediction model.

Run locally:
    python app/main.py

Or via gunicorn:
    gunicorn -b 0.0.0.0:8080 "app.main:create_app()"
"""

import os
from pathlib import Path

import joblib
import numpy as np
from flask import Flask, render_template, request

from hotel_prediction.logger import get_logger
from hotel_prediction.utils.io import read_yaml

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Paths (relative to project root)
# ---------------------------------------------------------------------------
MODEL_PATH = Path("artifacts/models/lgbm_model.pkl")
CONFIG_PATH = Path("config/config.yaml")


def create_app() -> Flask:
    """Application factory — creates and configures the Flask app."""
    _here = Path(__file__).parent
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
    logger.info(f"Model loaded from {MODEL_PATH}")

    @app.route("/", methods=["GET", "POST"])
    def index():
        prediction = None
        error = None

        if request.method == "POST":
            try:
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

                features = np.array([[
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
                ]])

                prediction = int(model.predict(features)[0])
                logger.info(f"Prediction: {prediction} for input features: {features.tolist()}")

            except (ValueError, KeyError) as e:
                error = f"Invalid input: {e}"
                logger.warning(f"Bad input from user: {e}")

        return render_template("index.html", prediction=prediction, error=error)

    @app.route("/health")
    def health():
        """Simple health-check endpoint."""
        return {"status": "ok", "model": str(MODEL_PATH)}, 200

    return app


if __name__ == "__main__":
    cfg = read_yaml(CONFIG_PATH).get("app", {})
    host = os.getenv("APP_HOST", cfg.get("host", "0.0.0.0"))
    port = int(os.getenv("APP_PORT", cfg.get("port", 8080)))
    debug = os.getenv("FLASK_DEBUG", str(cfg.get("debug", False))).lower() == "true"

    flask_app = create_app()
    flask_app.run(host=host, port=port, debug=debug)
