# Quick Start

Chạy thử project **hoàn toàn local** (không cần GCS, không cần Cloud Run) trong dưới 10 phút.

> **Điều kiện**: Đã hoàn thành [Installation](installation.md).

---

## Mục lục

- [Option A — Dùng data có sẵn (nhanh nhất)](#option-a--dùng-data-có-sẵn-nhanh-nhất)
- [Option B — Ingest từ GCS](#option-b--ingest-từ-gcs)
- [Khởi động Web App](#khởi-động-web-app)
- [Test prediction](#test-prediction)
- [Xem MLflow UI](#xem-mlflow-ui)

---

## Option A — Dùng data có sẵn (nhanh nhất)

Project đã có file `data/Hotel Reservations.csv`. Bỏ qua bước Data Ingestion (GCS), chạy thẳng từ file local:

### 1. Copy data vào thư mục raw

```bash
mkdir -p artifacts/raw
cp "data/Hotel Reservations.csv" artifacts/raw/raw.csv
```

### 2. Tạo train/test split

```python
# scripts/split_local.py (chạy 1 lần)
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

### 3. Chạy Preprocessing + Training

```bash
# Preprocessing (encode, SMOTE, feature selection)
python -m hotel_prediction.components.data_preprocessing

# Training (LightGBM + MLflow)
python -m hotel_prediction.components.model_trainer
```

Hoặc chạy toàn bộ pipeline (bỏ qua bước ingestion):

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

## Option B — Ingest từ GCS

Yêu cầu: GCS bucket đã có `Hotel_Reservations.csv`, credentials đã set trong `.env`.

```bash
# Chạy toàn bộ pipeline từ đầu
python -m hotel_prediction.pipelines.training_pipeline
```

Pipeline sẽ tự động:
1. Tải CSV từ GCS → `artifacts/raw/raw.csv`
2. Split → `train.csv` / `test.csv`
3. Preprocess → `artifacts/processed/`
4. Train + evaluate → `artifacts/models/lgbm_model.pkl`
5. Log tất cả vào MLflow

---

## Khởi động Web App

```bash
python src/app/main.py
```

Mặc định chạy tại: **http://localhost:8080**

Nếu muốn thay port:

```bash
APP_PORT=5000 python src/app/main.py
```

> **Lưu ý**: App sẽ báo lỗi nếu chưa có model. Hãy chạy training trước (Option A hoặc B).

---

## Test prediction

### Qua giao diện web

Mở trình duyệt tại `http://localhost:8080`, điền form và nhấn **Predict**.

### Qua curl (API)

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

## Xem MLflow UI

MLflow tự động lưu experiments trong `mlruns/` (local).

```bash
# Mở MLflow UI (terminal khác)
mlflow ui --port 5000
```

Truy cập: **http://localhost:5000**

Bạn sẽ thấy:
- Experiment runs với parameters, metrics (accuracy, precision, recall, F1)
- Artifacts: model file + datasets

---

## Cấu trúc artifacts sau khi chạy

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

Tiếp theo: [Training Guide](training.md) để hiểu chi tiết từng bước pipeline.
