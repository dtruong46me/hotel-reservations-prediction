# Quick Start

Run the project **completely local** (no GCS, no Cloud Run) in under 10 minutes.

> **Prerequisite**: Have completed [Installation](installation.md) and set up the environment.

---

## Table of Contents

- [Option A — Using existing data (fastest)](#option-a--using-existing-data-fastest)
- [Option B — Ingest from GCS](#option-b--ingest-from-gcs)
- [Launch Web App](#launch-web-app)
- [Test prediction](#test-prediction)
- [View MLflow UI](#view-mlflow-ui)

---

## Option A — Using existing data (fastest)

Project already has the file `data/Hotel Reservations.csv`. Skip the Data Ingestion step (GCS), and run directly from the local file. This is the fastest way to test the full pipeline and web app.:

### 1. Copy data into artifacts

```bash
mkdir -p artifacts/raw
cp "data/Hotel Reservations.csv" artifacts/raw/raw.csv
```

### 2. Create train/test split

```python
# scripts/split_local.py (run once to create train/test)
import pandas as pd
from sklearn.model_selection import train_test_split

df = pd.read_csv("artifacts/raw/raw.csv")
train, test = train_test_split(df, test_size=0.2, random_state=42)
train.to_csv("artifacts/raw/train.csv", index=False)
test.to_csv("artifacts/raw/test.csv", index=False)
print(f"Train: {len(train)} rows | Test: {len(test)} rows")
```

```bash
python -c "
import pandas as pd
from sklearn.model_selection import train_test_split
df = pd.read_csv('artifacts/raw/raw.csv')
train, test = train_test_split(df, test_size=0.2, random_state=42)
train.to_csv('artifacts/raw/train.csv', index=False)
test.to_csv('artifacts/raw/test.csv', index=False)
print(f'Train: {len(train)} | Test: {len(test)}')
"
```

### 3. Run Preprocessing + Training

```bash
# Preprocessing (encode, SMOTE, feature selection)
python -m hotel_prediction.components.data_preprocessing

# Training (LightGBM + MLflow)
python -m hotel_prediction.components.model_trainer
```

Or run the entire pipeline (skip the ingestion step since we already have the CSV):

```bash
python -c "
from hotel_prediction.components.data_preprocessing import DataPreprocessor, TRAIN_FILE_PATH, TEST_FILE_PATH, PROCESSED_DIR
from hotel_prediction.components.model_trainer import ModelTrainer, PROCESSED_TRAIN_PATH, PROCESSED_TEST_PATH, MODEL_OUTPUT_PATH, MODEL_PARAMS_PATH
from pathlib import Path

DataPreprocessor(TRAIN_FILE_PATH, TEST_FILE_PATH, PROCESSED_DIR, Path('config/config.yaml')).run()
ModelTrainer(PROCESSED_TRAIN_PATH, PROCESSED_TEST_PATH, MODEL_OUTPUT_PATH, MODEL_PARAMS_PATH).run()
print('Done! Model saved to:', MODEL_OUTPUT_PATH)
"
```

---

## Option B — Ingest from GCS

Prerequisite: GCS bucket already has `Hotel_Reservations.csv`, credentials set in `.env`.

```bash
# Run the entire pipeline from the beginning (including GCS ingestion)
python -m hotel_prediction.pipelines.training_pipeline
```

Pipeline will automatically:
1. Download CSV from GCS → `artifacts/raw/raw.csv`
2. Split → `train.csv` / `test.csv`
3. Preprocess → `artifacts/processed/`
4. Train + evaluate → `artifacts/models/lgbm_model.pkl`
5. Log everything into MLflow

---

## Launch Web App

```bash
python src/app/main.py
```

Default running at: **http://localhost:8080**

If you want to change the port:

```bash
APP_PORT=5000 python src/app/main.py
```

> **Note**: App will report an error if no model is available. Please run the training first (Option A or B).

---

## Test prediction

### Via web interface

Open the browser at `http://localhost:8080`, fill the form, and click **Predict**.

### Via curl (API)

```bash
curl -X POST http://localhost:8080/ \
  -d "lead_time=45" \
  -d "no_of_special_requests=1" \
  -d "avg_price_per_room=120.5" \
  -d "arrival_month=6" \
  -d "arrival_date=15" \
  -d "market_segment_type=4" \
  -d "no_of_week_nights=3" \
  -d "no_of_weekend_nights=1" \
  -d "type_of_meal_plan=0" \
  -d "room_type_reserved=1"
```

### Health check

```bash
curl http://localhost:8080/health
# {"status": "ok", "model": "artifacts/models/lgbm_model.pkl"}
```

---

## View MLflow UI

MLflow automatically saves experiments in `mlruns/` (local).

```bash
# Mở MLflow UI (another terminal)
mlflow ui --port 5000
```

Access: **http://localhost:5000**

You will see:
- Experiment runs with parameters, metrics (accuracy, precision, recall, F1)
- Artifacts: model file + datasets

---

## File structure of artifacts after running

```
artifacts/
├── raw/
│   ├── raw.csv            ← dataset gốc
│   ├── train.csv          ← 80% rows
│   └── test.csv           ← 20% rows
├── processed/
│   ├── processed_train.csv ← sau encode + SMOTE + feature select
│   └── processed_test.csv
└── models/
    └── lgbm_model.pkl     ← model đã trained
```

---

Next: [Training Guide](training.md) to know the pipeline.
