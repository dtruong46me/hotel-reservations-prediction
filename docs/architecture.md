# Architecture

Tổng quan về thiết kế kỹ thuật của project **Hotel Reservations Prediction**.

---

## Mục lục

- [Tổng quan hệ thống](#tổng-quan-hệ-thống)
- [Cấu trúc thư mục](#cấu-trúc-thư-mục)
- [Data flow](#data-flow)
- [Package design](#package-design)
- [Quyết định thiết kế](#quyết-định-thiết-kế)

---

## Tổng quan hệ thống

```
┌──────────────────────────────────────────────────────────────────┐
│                         DEVELOPER MACHINE                        │
│                                                                  │
│  config/             src/hotel_prediction/        src/app/       │
│  ├── config.yaml  →  ├── components/           →  ├── main.py   │
│  └── model_params    │   ├── data_ingestion        └── templates/│
│       .yaml          │   ├── data_preprocessing                  │
│                      │   └── model_trainer                       │
│                      └── pipelines/                              │
│                          └── training_pipeline                   │
└──────────────────┬───────────────────────────────────────────────┘
                   │ git push
                   ▼
┌──────────────────────────────────────────────────────────────────┐
│                        JENKINS (Docker DinD)                     │
│                                                                  │
│  Stage 1: Checkout repo                                          │
│  Stage 2: pip install dependencies                               │
│  Stage 3: docker build -f deploy/Dockerfile → push to GCR       │
│  Stage 4: gcloud run deploy → Cloud Run                          │
└──────────────────────────────────────────────────────────────────┘
                   │
         ┌─────────┴──────────┐
         ▼                    ▼
┌─────────────────┐  ┌────────────────────────────────────────────┐
│  Google Cloud   │  │           Google Cloud Run                  │
│  Storage (GCS)  │  │                                            │
│                 │  │  Container: src/app/main.py (gunicorn)     │
│ Hotel_Reserv    │  │  → POST /  → model.predict()              │
│ ations.csv      │  │  → GET /health                            │
└─────────────────┘  └────────────────────────────────────────────┘
         ↑
    DataIngestion downloads at training time (inside Docker build)
```

---

## Cấu trúc thư mục

```
hotel-reservations-prediction/
│
├── src/                              ← Toàn bộ source code
│   ├── hotel_prediction/             ← Core ML Python package
│   │   ├── __init__.py               (version, metadata)
│   │   ├── logger.py                 ← Cross-cutting: logging setup
│   │   ├── exception.py              ← Cross-cutting: custom exception
│   │   │
│   │   ├── components/               ← Pipeline steps (1 class = 1 trách nhiệm)
│   │   │   ├── data_ingestion.py     GCS download + train/test split
│   │   │   ├── data_preprocessing.py Encode + SMOTE + feature selection
│   │   │   └── model_trainer.py      LightGBM tune + evaluate + MLflow
│   │   │
│   │   ├── pipelines/                ← Orchestration
│   │   │   └── training_pipeline.py  Chạy 3 components theo thứ tự
│   │   │
│   │   └── utils/                    ← Pure utilities (không có side effects)
│   │       ├── __init__.py           Re-export để import ngắn gọn
│   │       ├── io.py                 read_yaml(), load_data()
│   │       └── ml_params.py          build_param_distributions()
│   │
│   └── app/                          ← Flask serving application
│       ├── __init__.py
│       ├── main.py                   Application factory (create_app())
│       ├── templates/
│       │   └── index.html            Prediction UI
│       └── static/
│           └── style.css             Dark glassmorphism theme
│
├── config/                           ← Tất cả config là YAML (không có .py)
│   ├── config.yaml                   App, ingestion, processing, MLflow settings
│   └── model_params.yaml             LightGBM hyperparameter distributions
│
├── deploy/                           ← Deployment configs
│   ├── Dockerfile                    Production: multi-stage, Python 3.11, gunicorn
│   └── jenkins/
│       └── Dockerfile                Jenkins với Docker-in-Docker
│
├── docs/                             ← Documentation (bạn đang đọc)
├── notebooks/                        ← EDA notebooks
├── tests/                            ← Unit tests
├── data/                             ← Raw input data (gitignored)
├── artifacts/                        ← ML outputs: raw, processed, models (gitignored)
├── logs/                             ← Operational logs (gitignored)
│
├── Jenkinsfile                       ← CI/CD pipeline definition
├── pyproject.toml                    ← Package metadata + dev deps
├── requirements.txt                  ← Runtime dependencies
└── .env.example                      ← Environment variable template
```

---

## Data flow

### Training time

```
GCS Bucket
    │
    │ google-cloud-storage client
    ▼
artifacts/raw/raw.csv
    │
    │ train_test_split(test_size=0.2, random_state=42)
    ▼
artifacts/raw/
├── train.csv  (80%)
└── test.csv   (20%)
    │
    │ LabelEncoder (categorical columns)
    │ log1p (skewed numerical columns, threshold=5)
    │ SMOTE (class balancing)
    │ RandomForestClassifier feature importance → top 10 features
    ▼
artifacts/processed/
├── processed_train.csv  (10 features + target)
└── processed_test.csv   (same 10 features + target)
    │
    │ RandomizedSearchCV(LGBMClassifier, n_iter=2, cv=2)
    │ Best model → evaluate on test set
    │ MLflow log params + metrics + artifacts
    ▼
artifacts/models/lgbm_model.pkl
```

### Serving time

```
HTTP POST /
    │
    │ Flask request.form → numpy array (10 features)
    ▼
joblib.load(artifacts/models/lgbm_model.pkl)
    │
    │ model.predict(features)
    ▼
prediction: 0 (likely cancel) or 1 (not cancel)
    │
    ▼
HTML response (render_template index.html)
```

---

## Package design

### Tại sao `src/` layout?

Dùng `src/` layout (thay vì để package ở root) giúp:
- Tránh import nhầm package local khi đang ở root directory
- `pip install -e .` rõ ràng về what is installed
- Tất cả source code trong một gốc, PYTHONPATH đơn giản: `src/`

### Tại sao `src/app/` trong `src/` (không phải `app/` ở root)?

- Tất cả **source code** (cả ML và web) nằm dưới một gốc `src/`
- Khi đọc project tree, rõ ràng hơn: `src/` = code, `config/` = config, `deploy/` = infra
- Import path nhất quán: cả `hotel_prediction` và `app` đều resolve từ `src/`

### Tại sao config toàn YAML?

- Không trộn Python code với configuration
- YAML đọc được bởi mọi tool (CI/CD, script bash, v.v.)
- Scipy distributions được parse tại runtime qua `build_param_distributions()`
- Dễ override qua env vars hoặc Helm values (khi dùng Kubernetes)

### `logger` và `exception` ở package root (không trong `utils/`)

Hai module này là **cross-cutting concerns** — mọi module đều dùng, không ai "sở hữu" chúng. Để ở root package `hotel_prediction/` phân biệt chúng với utilities có mục đích cụ thể.

### `utils/` được tách thành `io.py` và `ml_params.py`

| Module | Trách nhiệm | Dependencies |
|--------|------------|-------------|
| `io.py` | File I/O: YAML, CSV | `yaml`, `pandas` |
| `ml_params.py` | Parse scipy distributions | `scipy` only |

Tách ra để:
- Dễ test độc lập
- Không import `scipy` khi chỉ cần đọc YAML
- Rõ ràng về dependency graph

---

## Quyết định thiết kế

### Không có `model/` package riêng

Model là `LGBMClassifier` (sklearn API), không có custom logic. Không cần `model/` package trừ khi có:
- Custom model class
- Feature preprocessing cần reproduce tại serve time
- Custom prediction logic

### Không cần `paths_config.py`

Paths được define trực tiếp trong từng component (dùng `pathlib.Path`). Mỗi component là self-contained, không cần import global path constants.

### Training pipeline trong Docker build vs. separate

Thiết kế hiện tại: training chạy **trong Docker build** (tại CI/CD). Sau khi train xong, model được bake vào image cùng với app. Đây là approach đơn giản cho project nhỏ.

Cho production lớn hơn, nên tách:
1. **Training job**: chạy riêng (Cloud Run Jobs hoặc Vertex AI)
2. **Serving container**: chỉ chứa model file (từ GCS) + app

### Gunicorn thay vì Flask dev server

`flask run` / `app.run()` không phù hợp cho production (single-threaded, no worker management). Gunicorn với `--workers 2` xử lý concurrent requests tốt hơn và là standard trong production Flask deployment.
