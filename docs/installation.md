# Installation Guide

Hướng dẫn cài đặt môi trường đầy đủ để chạy project **Hotel Reservations Prediction** — cả local development lẫn production deployment.

---

## Mục lục

- [Prerequisites](#prerequisites)
- [Bước 1 — Clone repository](#bước-1--clone-repository)
- [Bước 2 — Cài đặt Python environment](#bước-2--cài-đặt-python-environment)
- [Bước 3 — Cấu hình environment variables](#bước-3--cấu-hình-environment-variables)
- [Bước 4 — Cài đặt Google Cloud SDK (nếu deploy)](#bước-4--cài-đặt-google-cloud-sdk-nếu-deploy)
- [Bước 5 — Xác minh cài đặt](#bước-5--xác-minh-cài-đặt)

---

## Prerequisites

### Bắt buộc (local development)

| Công cụ | Phiên bản tối thiểu | Kiểm tra |
|---------|---------------------|---------|
| Python | 3.10+ | `python --version` |
| pip | 23+ | `pip --version` |
| Git | bất kỳ | `git --version` |

### Cần thêm (nếu dùng GCS để ingest data)

| Công cụ | Ghi chú |
|---------|---------|
| Google Cloud account | Cần billing được bật |
| GCP Service Account Key | JSON key file với quyền `Storage Object Viewer` |
| Google Cloud SDK (`gcloud`) | Hoặc chỉ cần set `GOOGLE_APPLICATION_CREDENTIALS` |

### Cần thêm (nếu deploy lên Cloud Run)

| Công cụ | Ghi chú |
|---------|---------|
| Docker Desktop | Chạy background, version 20+ |
| GCP Project | Cloud Run API + Container Registry API phải được bật |
| Jenkins | Setup theo [Deployment Guide](deployment.md) |

---

## Bước 1 — Clone repository

```bash
git clone https://github.com/your-org/hotel-reservations-prediction.git
cd hotel-reservations-prediction
```

---

## Bước 2 — Cài đặt Python environment

### Tạo virtual environment

```bash
# Tạo venv
python -m venv venv

# Kích hoạt
# macOS / Linux:
source venv/bin/activate

# Windows (PowerShell):
venv\Scripts\Activate.ps1

# Windows (CMD):
venv\Scripts\activate.bat
```

> **Lưu ý**: Luôn đảm bảo `(venv)` xuất hiện ở đầu terminal trước khi chạy bất kỳ lệnh nào.

### Cài đặt dependencies

```bash
# Runtime dependencies (bắt buộc)
pip install --upgrade pip
pip install -r requirements.txt

# Cài đặt package ở chế độ editable
# (cần thiết để import hotel_prediction và app hoạt động đúng)
pip install -e .
```

### Cài thêm dev dependencies (tùy chọn — cho testing, linting)

```bash
pip install -e ".[dev]"
```

Bao gồm: `pytest`, `pytest-cov`, `black`, `isort`, `flake8`.

---

## Bước 3 — Cấu hình environment variables

```bash
# Copy template
cp .env.example .env
```

Mở `.env` và điền các giá trị:

```env
# Google Cloud
GCP_PROJECT_ID=your-gcp-project-id
GCP_BUCKET_NAME=your-gcs-bucket-name
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/your/service-account-key.json

# MLflow (bỏ qua nếu chưa cần tracking)
MLFLOW_TRACKING_URI=http://localhost:5000

# Flask App (optional — mặc định 0.0.0.0:8080)
APP_HOST=0.0.0.0
APP_PORT=8080
FLASK_DEBUG=false
```

> **Quan trọng**: File `.env` đã được gitignore. Không commit file này lên repository.

Nếu bạn đang dùng **Linux/macOS**, load env vars vào shell:

```bash
export $(grep -v '^#' .env | xargs)
```

Nếu dùng **Windows PowerShell**:

```powershell
Get-Content .env | Where-Object { $_ -notmatch '^#' -and $_ -ne '' } | ForEach-Object {
    $key, $value = $_ -split '=', 2
    [System.Environment]::SetEnvironmentVariable($key, $value, 'Process')
}
```

---

## Bước 4 — Cài đặt Google Cloud SDK (nếu deploy)

### macOS

```bash
brew install --cask google-cloud-sdk
gcloud init
```

### Linux (Debian/Ubuntu)

```bash
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
gcloud init
```

### Windows

Tải installer từ: https://cloud.google.com/sdk/docs/install

Sau khi cài:

```bash
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

---

## Bước 5 — Xác minh cài đặt

Chạy lệnh sau để kiểm tra toàn bộ:

```bash
python - <<'EOF'
import hotel_prediction
print(f"✅ hotel_prediction package: v{hotel_prediction.__version__}")

import app.main
print("✅ Flask app importable")

from hotel_prediction.utils.io import read_yaml
cfg = read_yaml("config/config.yaml")
print(f"✅ config.yaml loaded: {list(cfg.keys())}")

from hotel_prediction.utils.ml_params import build_param_distributions
params_cfg = read_yaml("config/model_params.yaml")
dists = build_param_distributions(params_cfg["lightgbm"]["param_distributions"])
print(f"✅ model_params.yaml loaded: {list(dists.keys())}")
EOF
```

Nếu tất cả hiện `✅`, bạn đã cài đặt thành công. Tiếp theo xem [Quick Start](quickstart.md).
