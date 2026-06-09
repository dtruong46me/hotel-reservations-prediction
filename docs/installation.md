# Installation Guide

Guide to set up the full environment for running the **Hotel Reservations Prediction** project — both for local development and production deployment.
---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Step 1 — Clone repository](#step-1--clone-repository)
- [Step 2 — Install Python environment](#step-2--install-python-environment)
- [Step 3 — Configure environment variables](#step-3--configure-environment-variables)
- [Step 4 — Install Google Cloud SDK (if deploying)](#step-4--install-google-cloud-sdk-if-deploying)
- [Step 5 — Verify installation](#step-5--verify-installation)

---

## Prerequisites

### Required (local development)

| Tool | Minimum Version | Check |
|---------|---------------------|---------|
| Python | 3.10+ | `python --version` |
| pip | 23+ | `pip --version` |
| Git | any | `git --version` |

### Additional (if using GCS for data ingestion or MLflow tracking)

| Tool | Note |
|---------|---------|
| Google Cloud account | Billing must be enabled |
| GCP Service Account Key | JSON key file with `Storage Object Viewer` permissions |
| Google Cloud SDK (`gcloud`) | Or simply set `GOOGLE_APPLICATION_CREDENTIALS` |

### Additional (if deploying to Cloud Run)

| Tool | Note |
|---------|---------|
| Docker Desktop | Chạy background, version 20+ |
| GCP Project | Cloud Run API + Container Registry API phải được bật |
| Jenkins | Setup theo [Deployment Guide](deployment.md) |

---

## Step 1 — Clone repository

```bash
git clone https://github.com/your-org/hotel-reservations-prediction.git
cd hotel-reservations-prediction
```

---

## Step 2 — Install Python environment

### Using Conda (Recommended)

```bash
# Create conda environment
conda create -n hotel-prediction python=3.10 -y

# Activate
conda activate hotel-prediction

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install package in editable mode
pip install -e .
```

### Create virtual environment with `venv` (Alternative)

```bash
# Create venv
python -m venv venv

# Activate
# macOS / Linux:
source venv/bin/activate

# Windows (PowerShell):
venv\Scripts\Activate.ps1

# Windows (CMD):
venv\Scripts\activate.bat

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install package in editable mode
pip install -e .
```

> **Note**: Always ensure `(venv)` appears at the beginning of the terminal prompt before running any commands.

### Install additional dev dependencies (optional — for testing, linting)

```bash
pip install -e ".[dev]"
```

Include: `pytest`, `pytest-cov`, `black`, `isort`, `flake8`.

---

## Step 3 — Configure environment variables

```bash
# Copy template
cp .env.example .env
```

Open `.env` and fill in the values for your environment. Example:

```env
# Google Cloud
GCP_PROJECT_ID=your-gcp-project-id
GCP_BUCKET_NAME=your-gcs-bucket-name
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/your/service-account-key.json

# MLflow (skip if not needed)
MLFLOW_TRACKING_URI=http://localhost:5000

# Flask App (optional — default 0.0.0.0:8080)
APP_HOST=0.0.0.0
APP_PORT=8080
FLASK_DEBUG=false
```

> **Important**: File `.env` must be gitignore. Do not commit this file to repository.

If using **Linux/macOS**, load env vars into the shell:

```bash
export $(grep -v '^#' .env | xargs)
```

If using **Windows PowerShell**:

```powershell
Get-Content .env | Where-Object { $_ -notmatch '^#' -and $_ -ne '' } | ForEach-Object {
    $key, $value = $_ -split '=', 2
    [System.Environment]::SetEnvironmentVariable($key, $value, 'Process')
}
```

---

## Step 4 — Install Google Cloud SDK (if deploying or using GCS)

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

## Step 5 — Verify Installation

Run the following command to check everything is set up correctly:

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

If all lines show `✅`, you have successfully installed the package. Next, see [Quick Start](quickstart.md).
