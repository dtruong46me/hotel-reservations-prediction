# Training Guide

Hướng dẫn chi tiết về **ML training pipeline** — từ cấu hình, chạy từng bước, đến theo dõi experiments với MLflow.

---

## Mục lục

- [Tổng quan pipeline](#tổng-quan-pipeline)
- [Cấu hình](#cấu-hình)
  - [config.yaml](#configyaml)
  - [model_params.yaml](#model_paramsyaml)
- [Bước 1 — Data Ingestion](#bước-1--data-ingestion)
- [Bước 2 — Data Preprocessing](#bước-2--data-preprocessing)
- [Bước 3 — Model Training](#bước-3--model-training)
- [Chạy toàn bộ pipeline](#chạy-toàn-bộ-pipeline)
- [MLflow Tracking](#mlflow-tracking)
- [Tuning hyperparameters](#tuning-hyperparameters)
- [Output artifacts](#output-artifacts)

---

## Tổng quan pipeline

```
┌─────────────────┐    ┌──────────────────────┐    ┌───────────────────┐
│  Data Ingestion  │───▶│  Data Preprocessing   │───▶│  Model Training   │
│                 │    │                      │    │                   │
│ GCS → raw CSV   │    │ Encode + SMOTE       │    │ LightGBM + CV     │
│ Split 80/20     │    │ Feature Selection    │    │ MLflow logging    │
└─────────────────┘    └──────────────────────┘    └───────────────────┘
        ↓                        ↓                          ↓
  artifacts/raw/         artifacts/processed/        artifacts/models/
```

Mỗi bước là một **class độc lập** trong `src/hotel_prediction/components/`, có thể chạy riêng lẻ hoặc qua `training_pipeline.py`.

---

## Cấu hình

### config.yaml

File: [`config/config.yaml`](../config/config.yaml)

```yaml
data_ingestion:
  bucket_name: "my_bucket9789"       # Tên GCS bucket
  bucket_file_name: "Hotel_Reservations.csv"
  train_ratio: 0.8                    # 80% train, 20% test

data_processing:
  categorical_columns: [...]          # Cột sẽ được LabelEncode
  numerical_columns: [...]            # Cột sẽ được check skewness
  skewness_threshold: 5               # Cột có skew > 5 → log1p transform
  no_of_features: 10                  # Số features giữ lại sau selection

mlflow:
  experiment_name: "hotel-reservations-prediction"
  tracking_uri: "http://localhost:5000"

app:
  host: "0.0.0.0"
  port: 8080
```

**Cách override không cần sửa file:**

```bash
# Đổi bucket name qua env var
GCP_BUCKET_NAME=other-bucket python -m hotel_prediction.pipelines.training_pipeline
```

### model_params.yaml

File: [`config/model_params.yaml`](../config/model_params.yaml)

```yaml
lightgbm:
  param_distributions:
    n_estimators:   {type: randint, low: 100, high: 500}
    max_depth:      {type: randint, low: 5, high: 50}
    learning_rate:  {type: uniform, loc: 0.01, scale: 0.2}
    num_leaves:     {type: randint, low: 20, high: 100}
    boosting_type:  [gbdt, dart, goss]  # plain list → sampled uniformly

  random_search:
    n_iter: 2       # Số combinations thử (tăng lên 20-50 khi prod)
    cv: 2           # Cross-validation folds
    n_jobs: -1      # Dùng toàn bộ CPU
    scoring: accuracy
    random_state: 42
```

> **Lưu ý production**: `n_iter: 2` rất thấp, chỉ dùng để test nhanh. Khi train thật, tăng lên `n_iter: 20` và `cv: 5`.

Supported distribution types:
| Type | Parameters | Ví dụ |
|------|-----------|-------|
| `randint` | `low`, `high` | `{type: randint, low: 100, high: 500}` |
| `uniform` | `loc`, `scale` | `{type: uniform, loc: 0.01, scale: 0.2}` |
| plain list | — | `[gbdt, dart, goss]` |

---

## Bước 1 — Data Ingestion

**Class**: `DataIngestion` — `src/hotel_prediction/components/data_ingestion.py`

**Đầu vào**: GCS bucket  
**Đầu ra**: `artifacts/raw/raw.csv`, `train.csv`, `test.csv`

```bash
python -m hotel_prediction.components.data_ingestion
```

Quá trình:
1. Kết nối GCS qua `google-cloud-storage` (cần `GOOGLE_APPLICATION_CREDENTIALS`)
2. Download file CSV về `artifacts/raw/raw.csv`
3. Split theo `train_ratio` (stratified random, seed=42)
4. Lưu `train.csv` và `test.csv`

**Bỏ qua nếu không có GCS**: Copy thủ công và split bằng script (xem [Quick Start](quickstart.md)).

---

## Bước 2 — Data Preprocessing

**Class**: `DataPreprocessor` — `src/hotel_prediction/components/data_preprocessing.py`

**Đầu vào**: `artifacts/raw/train.csv`, `test.csv`  
**Đầu ra**: `artifacts/processed/processed_train.csv`, `processed_test.csv`

```bash
python -m hotel_prediction.components.data_preprocessing
```

Chi tiết xử lý:

### 2a. Encode & Clean
- Drop cột `Unnamed: 0`, `Booking_ID`
- Dedup rows
- **LabelEncoding** cho categorical columns (mapping được log lại)
- **Log1p transform** cho numerical columns có skew > `skewness_threshold`

### 2b. Class Balancing — SMOTE
Dataset gốc có imbalance (tỷ lệ cancel vs. không cancel lệch nhau). SMOTE (Synthetic Minority Over-sampling Technique) tạo thêm samples tổng hợp cho class thiểu số.

```
Before SMOTE: {0: 24390, 1: 12345}  (giả sử)
After SMOTE:  {0: 24390, 1: 24390}
```

> **Lưu ý**: SMOTE áp dụng cho cả train lẫn test — đây là thiết kế hiện tại của project. Trong production thực tế, thường chỉ SMOTE trên train set.

### 2c. Feature Selection — Random Forest Importance
Dùng `RandomForestClassifier` để tính feature importance, giữ lại `no_of_features` (mặc định: 10) features quan trọng nhất.

Features được chọn sẽ được dùng **nhất quán** cho cả train và test set.

---

## Bước 3 — Model Training

**Class**: `ModelTrainer` — `src/hotel_prediction/components/model_trainer.py`

**Đầu vào**: `artifacts/processed/processed_train.csv`, `processed_test.csv`  
**Đầu ra**: `artifacts/models/lgbm_model.pkl`

```bash
python -m hotel_prediction.components.model_trainer
```

Chi tiết:

### 3a. Hyperparameter Tuning
`RandomizedSearchCV` với LightGBM Classifier:
- Số iterations: `n_iter` (từ `model_params.yaml`)
- Cross-validation: `cv` folds
- Scoring metric: accuracy
- Best model được chọn tự động

### 3b. Evaluation
Báo cáo các metrics trên test set:
- **Accuracy** — tỷ lệ dự đoán đúng
- **Precision** — trong số dự báo "sẽ hủy", bao nhiêu đúng
- **Recall** — trong số thực sự hủy, bắt được bao nhiêu
- **F1 Score** — harmonic mean của precision và recall

### 3c. MLflow Logging
Tự động log:
- Parameters: toàn bộ hyperparameters của best model
- Metrics: accuracy, precision, recall, f1
- Artifacts: model file + train/test datasets

---

## Chạy toàn bộ pipeline

```bash
# Cần GCS credentials
python -m hotel_prediction.pipelines.training_pipeline
```

Hoặc import trong Python:

```python
from hotel_prediction.pipelines.training_pipeline import run_training_pipeline
run_training_pipeline()
```

---

## MLflow Tracking

### Khởi động MLflow server

```bash
# Terminal riêng
mlflow ui --port 5000 --backend-store-uri mlruns/
```

Truy cập: `http://localhost:5000`

### Xem experiments

Mỗi lần chạy `ModelTrainer.run()` tạo một **MLflow run** mới với:

```
Run
├── Parameters
│   ├── n_estimators: 347
│   ├── max_depth: 23
│   ├── learning_rate: 0.087
│   └── ...
├── Metrics
│   ├── accuracy: 0.8923
│   ├── precision: 0.8712
│   ├── recall: 0.8543
│   └── f1: 0.8627
└── Artifacts
    ├── datasets/
    │   ├── processed_train.csv
    │   └── processed_test.csv
    └── lgbm_model.pkl
```

### So sánh experiments

MLflow UI cho phép so sánh nhiều runs, plot metrics theo thời gian — hữu ích khi thay đổi hyperparameter ranges.

---

## Tuning hyperparameters

Để cải thiện model, chỉnh `config/model_params.yaml`:

```yaml
lightgbm:
  param_distributions:
    n_estimators: {type: randint, low: 200, high: 1000}  # tăng range
    max_depth:    {type: randint, low: 10, high: 100}
    learning_rate: {type: uniform, loc: 0.005, scale: 0.1}
    num_leaves:   {type: randint, low: 31, high: 300}
    min_child_samples: {type: randint, low: 5, high: 50}  # thêm param mới

  random_search:
    n_iter: 30      # tăng từ 2 lên 30 để search kỹ hơn
    cv: 5           # 5-fold CV
    scoring: f1     # đổi sang F1 nếu imbalanced dataset
```

Sau khi chỉnh, chạy lại:

```bash
python -m hotel_prediction.components.model_trainer
```

So sánh kết quả trong MLflow UI.

---

## Output artifacts

| File | Kích thước điển hình | Mô tả |
|------|---------------------|-------|
| `artifacts/raw/raw.csv` | ~5-10 MB | Dataset gốc từ GCS |
| `artifacts/raw/train.csv` | ~4-8 MB | 80% rows |
| `artifacts/raw/test.csv` | ~1-2 MB | 20% rows |
| `artifacts/processed/processed_train.csv` | ~2-4 MB | Sau encode + SMOTE + feature select |
| `artifacts/processed/processed_test.csv` | ~0.5-1 MB | Cùng feature schema |
| `artifacts/models/lgbm_model.pkl` | ~1-5 MB | Trained LightGBM model |

Tất cả artifacts được gitignore. Khi deploy, model cần được build vào Docker image hoặc mount từ GCS.
