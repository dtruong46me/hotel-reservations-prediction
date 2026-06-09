# Deployment Guide — Full A to Z

Hướng dẫn deploy **Hotel Reservations Prediction** lên Google Cloud Run thông qua Jenkins CI/CD pipeline, từ đầu đến khi có URL public để test thật.

> **Thời gian dự kiến**: 60–90 phút lần đầu setup.

---

## Mục lục

- [Prerequisites](#prerequisites)
- [Phần 1 — Chuẩn bị Google Cloud Platform](#phần-1--chuẩn-bị-google-cloud-platform)
  - [1.1 Tạo GCP Project](#11-tạo-gcp-project)
  - [1.2 Bật các GCP APIs](#12-bật-các-gcp-apis)
  - [1.3 Tạo GCS Bucket và upload data](#13-tạo-gcs-bucket-và-upload-data)
  - [1.4 Tạo Service Account](#14-tạo-service-account)
  - [1.5 Tải Service Account Key](#15-tải-service-account-key)
- [Phần 2 — Chuẩn bị Jenkins](#phần-2--chuẩn-bị-jenkins)
  - [2.1 Build Jenkins image](#21-build-jenkins-image)
  - [2.2 Run Jenkins container](#22-run-jenkins-container)
  - [2.3 Truy cập Jenkins lần đầu](#23-truy-cập-jenkins-lần-đầu)
  - [2.4 Cài Python trong Jenkins](#24-cài-python-trong-jenkins)
  - [2.5 Cài Google Cloud SDK trong Jenkins](#25-cài-google-cloud-sdk-trong-jenkins)
  - [2.6 Cấp Docker permissions](#26-cấp-docker-permissions)
- [Phần 3 — Cấu hình Jenkins Credentials](#phần-3--cấu-hình-jenkins-credentials)
  - [3.1 Thêm GitHub token](#31-thêm-github-token)
  - [3.2 Thêm GCP Service Account key](#32-thêm-gcp-service-account-key)
- [Phần 4 — Tạo và chạy Pipeline Job](#phần-4--tạo-và-chạy-pipeline-job)
  - [4.1 Cập nhật Jenkinsfile](#41-cập-nhật-jenkinsfile)
  - [4.2 Tạo pipeline job trong Jenkins](#42-tạo-pipeline-job-trong-jenkins)
  - [4.3 Trigger build lần đầu](#43-trigger-build-lần-đầu)
- [Phần 5 — Xác minh và Test](#phần-5--xác-minh-và-test)
  - [5.1 Xem logs build](#51-xem-logs-build)
  - [5.2 Kiểm tra GCR image](#52-kiểm-tra-gcr-image)
  - [5.3 Kiểm tra Cloud Run service](#53-kiểm-tra-cloud-run-service)
  - [5.4 Test endpoint thật](#54-test-endpoint-thật)
- [Phần 6 — Tự động hoá (Webhook)](#phần-6--tự-động-hoá-webhook)
- [Phần 7 — Troubleshooting](#phần-7--troubleshooting)

---

## Prerequisites

Cài sẵn trên máy cục bộ của bạn:

| Công cụ | Phiên bản | Kiểm tra |
|---------|----------|---------|
| Docker Desktop | 20+ | `docker --version` |
| Git | bất kỳ | `git --version` |
| Google Cloud SDK | bất kỳ | `gcloud --version` |
| Trình duyệt web | bất kỳ | — |

Tài khoản / quyền truy cập:

| Yêu cầu | Ghi chú |
|---------|---------|
| Google account | Gmail hoặc Workspace |
| GCP billing account | Cloud Run tính phí nhưng có free tier khá rộng |
| GitHub account | Nếu repo là private, cần tạo Personal Access Token |

---

## Phần 1 — Chuẩn bị Google Cloud Platform

### 1.1 Tạo GCP Project

```bash
# Đăng nhập (mở browser)
gcloud auth login

# Tạo project mới (đặt tên dễ nhớ)
gcloud projects create hotel-prediction-prod --name="Hotel Prediction"

# Set project làm default
gcloud config set project hotel-prediction-prod

# Xác nhận
gcloud config get project
# → hotel-prediction-prod
```

> Nếu đã có project, chỉ cần: `gcloud config set project YOUR_PROJECT_ID`

### 1.2 Bật các GCP APIs

```bash
gcloud services enable \
  run.googleapis.com \
  containerregistry.googleapis.com \
  storage.googleapis.com \
  cloudbuild.googleapis.com \
  iam.googleapis.com
```

Đợi ~1-2 phút cho APIs được kích hoạt. Kiểm tra:

```bash
gcloud services list --enabled | grep -E "run|storage|container"
```

### 1.3 Tạo GCS Bucket và upload data

```bash
# Tạo bucket (tên phải unique toàn cầu)
# Thay "hotel-prediction-data-2024" bằng tên của bạn
BUCKET_NAME="hotel-prediction-data-$(date +%s)"
gcloud storage buckets create gs://$BUCKET_NAME --location=us-central1

echo "Bucket name: $BUCKET_NAME"
# Ghi lại tên này, sẽ dùng trong config.yaml

# Upload dataset
gcloud storage cp "data/Hotel Reservations.csv" gs://$BUCKET_NAME/Hotel_Reservations.csv

# Xác nhận
gcloud storage ls gs://$BUCKET_NAME/
```

Cập nhật `config/config.yaml`:

```yaml
data_ingestion:
  bucket_name: "hotel-prediction-data-XXXXX"  # ← Điền bucket name vừa tạo
  bucket_file_name: "Hotel_Reservations.csv"
```

### 1.4 Tạo Service Account

```bash
# Tạo service account
gcloud iam service-accounts create jenkins-deployer \
  --display-name="Jenkins CI/CD Deployer"

# Lấy email của service account
SA_EMAIL="jenkins-deployer@hotel-prediction-prod.iam.gserviceaccount.com"

# Gán các roles cần thiết
gcloud projects add-iam-policy-binding hotel-prediction-prod \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/storage.objectViewer"

gcloud projects add-iam-policy-binding hotel-prediction-prod \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/storage.objectAdmin"

gcloud projects add-iam-policy-binding hotel-prediction-prod \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding hotel-prediction-prod \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/iam.serviceAccountUser"

gcloud projects add-iam-policy-binding hotel-prediction-prod \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/storage.admin"
```

### 1.5 Tải Service Account Key

```bash
# Tạo và tải key JSON
gcloud iam service-accounts keys create \
  ./secrets/gcp-service-account-key.json \
  --iam-account=$SA_EMAIL

echo "Key saved to: ./secrets/gcp-service-account-key.json"
```

> ⚠️ **Bảo mật**: File `secrets/` đã được gitignore. Không commit file này. Lưu ở chỗ an toàn.

---

## Phần 2 — Chuẩn bị Jenkins

### 2.1 Build Jenkins image

Jenkins cần Docker-in-Docker (DinD) để có thể build và push Docker images trong pipeline.

```bash
# Build Jenkins image với Docker support
docker build -t jenkins-dind -f deploy/jenkins/Dockerfile .

# Xác nhận image đã build
docker images | grep jenkins-dind
```

### 2.2 Run Jenkins container

```bash
docker run -d --name jenkins-dind \
  --privileged \
  -p 8080:8080 \
  -p 50000:50000 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v jenkins_home:/var/jenkins_home \
  jenkins-dind
```

> **Windows**: Nếu dùng Docker Desktop trên Windows, thay `/var/run/docker.sock` thành `//var/run/docker.sock`

Đợi ~30 giây rồi kiểm tra:

```bash
docker ps | grep jenkins-dind
docker logs jenkins-dind 2>&1 | tail -20
```

### 2.3 Truy cập Jenkins lần đầu

```bash
# Lấy admin password từ logs
docker logs jenkins-dind 2>&1 | grep -A 3 "Please use the following password"
```

Hoặc:

```bash
docker exec jenkins-dind cat /var/jenkins_home/secrets/initialAdminPassword
```

1. Mở trình duyệt: **http://localhost:8080**
2. Paste admin password vừa lấy
3. Chọn **"Install suggested plugins"** → đợi ~5 phút
4. Tạo user admin của bạn (ghi nhớ username + password)
5. Nhấn **"Start using Jenkins"**

### 2.4 Cài Python trong Jenkins

```bash
# Vào shell bên trong Jenkins container
docker exec -u root -it jenkins-dind bash

# Cài Python 3 + pip + venv
apt-get update -y
apt-get install -y python3 python3-pip python3-venv
ln -sf /usr/bin/python3 /usr/bin/python
python --version
pip3 --version

# Thoát container
exit

# Restart Jenkins
docker restart jenkins-dind
```

Đợi ~30 giây, đăng nhập lại vào http://localhost:8080.

### 2.5 Cài Google Cloud SDK trong Jenkins

```bash
docker exec -u root -it jenkins-dind bash

# Cài gcloud
apt-get install -y curl apt-transport-https ca-certificates gnupg
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -
echo "deb https://packages.cloud.google.com/apt cloud-sdk main" \
  | tee /etc/apt/sources.list.d/google-cloud-sdk.list
apt-get update
apt-get install -y google-cloud-sdk

# Xác nhận
gcloud --version

exit
```

### 2.6 Cấp Docker permissions

```bash
docker exec -u root -it jenkins-dind bash

groupadd -f docker
usermod -aG docker jenkins

exit

# Restart để áp dụng group changes
docker restart jenkins-dind
```

Đăng nhập lại sau ~30 giây.

---

## Phần 3 — Cấu hình Jenkins Credentials

### 3.1 Thêm GitHub token

> Cần nếu repository là **private**. Nếu public, có thể bỏ qua.

1. Tạo GitHub Personal Access Token:
   - GitHub → Settings → Developer Settings → Personal access tokens → Tokens (classic)
   - Generate new token, chọn scope: `repo` (full control)
   - Copy token (chỉ hiện một lần)

2. Thêm vào Jenkins:
   - Jenkins → **Dashboard** → **Manage Jenkins** → **Credentials**
   - Click **(global)** → **Add Credentials**
   - Kind: **Username with password**
   - Username: GitHub username của bạn
   - Password: paste token vừa tạo
   - ID: `github-token` ← **phải đúng chính xác**
   - Description: "GitHub Personal Access Token"
   - **Save**

### 3.2 Thêm GCP Service Account key

1. Jenkins → **Dashboard** → **Manage Jenkins** → **Credentials**
2. Click **(global)** → **Add Credentials**
3. Kind: **Secret file**
4. File: Upload `secrets/gcp-service-account-key.json`
5. ID: `gcp-key` ← **phải đúng chính xác**
6. Description: "GCP Service Account Key for Jenkins"
7. **Save**

---

## Phần 4 — Tạo và chạy Pipeline Job

### 4.1 Cập nhật Jenkinsfile

Mở `Jenkinsfile` và cập nhật các giá trị sau:

```groovy
environment {
    VENV_DIR    = 'venv'
    GCP_PROJECT = "hotel-prediction-prod"   // ← Project ID của bạn
    GCLOUD_PATH = "/var/jenkins_home/google-cloud-sdk/bin"
    IMAGE_NAME  = "gcr.io/${GCP_PROJECT}/hotel-prediction"
    IMAGE_TAG   = "latest"
}
```

Và trong stage Checkout, cập nhật URL repository:

```groovy
url: 'https://github.com/YOUR_USERNAME/hotel-reservations-prediction.git'
```

Commit và push:

```bash
git add Jenkinsfile config/config.yaml
git commit -m "feat: configure GCP project and bucket for deployment"
git push origin main
```

### 4.2 Tạo pipeline job trong Jenkins

1. Jenkins Dashboard → **New Item**
2. Tên: `hotel-prediction-pipeline`
3. Chọn: **Pipeline** → **OK**
4. Trong phần **Pipeline**:
   - Definition: **Pipeline script from SCM**
   - SCM: **Git**
   - Repository URL: `https://github.com/YOUR_USERNAME/hotel-reservations-prediction.git`
   - Credentials: chọn `github-token` (nếu private repo)
   - Branch: `*/main`
   - Script Path: `Jenkinsfile`
5. **Save**

### 4.3 Trigger build lần đầu

1. Mở job `hotel-prediction-pipeline`
2. Click **"Build Now"** ở sidebar trái
3. Click vào build #1 trong Build History
4. Click **"Console Output"** để xem logs realtime

Build sẽ chạy qua 4 stages (~5-15 phút):

```
[Checkout]                ✓ ~10s
[Setup Python Environment] ✓ ~2-5 min
[Build & Push Docker Image] ✓ ~5-10 min (lần đầu lâu hơn)
[Deploy to Cloud Run]      ✓ ~1-2 min
```

---

## Phần 5 — Xác minh và Test

### 5.1 Xem logs build

Nếu build fail, xem console output và tìm dòng lỗi đầu tiên có `ERROR` hoặc `FAILED`.

Common issues: xem [Troubleshooting](#phần-7--troubleshooting).

### 5.2 Kiểm tra GCR image

```bash
# List images trong GCR
gcloud container images list --repository=gcr.io/hotel-prediction-prod

# Xem tags của image
gcloud container images list-tags gcr.io/hotel-prediction-prod/hotel-prediction
```

### 5.3 Kiểm tra Cloud Run service

```bash
# List services
gcloud run services list --region=us-central1

# Mô tả service
gcloud run services describe hotel-prediction --region=us-central1

# Lấy URL
SERVICE_URL=$(gcloud run services describe hotel-prediction \
  --region=us-central1 \
  --format='value(status.url)')
echo "Service URL: $SERVICE_URL"
```

### 5.4 Test endpoint thật

```bash
# Health check
curl $SERVICE_URL/health
# Expected: {"model": "artifacts/models/lgbm_model.pkl", "status": "ok"}

# Prediction request
curl -X POST $SERVICE_URL/ \
  -d "lead_time=45" \
  -d "no_of_special_requests=2" \
  -d "avg_price_per_room=115.0" \
  -d "arrival_month=8" \
  -d "arrival_date=20" \
  -d "market_segment_type=4" \
  -d "no_of_week_nights=3" \
  -d "no_of_weekend_nights=2" \
  -d "type_of_meal_plan=0" \
  -d "room_type_reserved=0"
```

Hoặc mở URL trong trình duyệt để dùng giao diện web.

### Bảng test cases gợi ý

| Scenario | lead_time | price | special_req | Kết quả dự kiến |
|----------|-----------|-------|-------------|----------------|
| Booking sớm, giá cao | 200 | 250.0 | 0 | Có thể cancel (0) |
| Booking gần, nhiều request | 5 | 100.0 | 3 | Không cancel (1) |
| Corporate, giá trung bình | 30 | 120.0 | 1 | Tùy model |

---

## Phần 6 — Tự động hoá (Webhook)

Để pipeline tự chạy khi có `git push`:

### Cấu hình GitHub Webhook

1. **GitHub repo** → Settings → Webhooks → **Add webhook**
2. Payload URL: `http://YOUR_JENKINS_PUBLIC_IP:8080/github-webhook/`
3. Content type: `application/json`
4. Events: chọn **"Just the push event"**
5. **Add webhook**

> **Lưu ý**: Jenkins phải có public IP. Nếu chạy local, dùng [ngrok](https://ngrok.com) để expose:
> ```bash
> ngrok http 8080
> # Dùng URL ngrok làm Payload URL
> ```

### Cấu hình Jenkins Job

Trong job settings → **Build Triggers** → chọn **"GitHub hook trigger for GITScm polling"** → Save.

Từ giờ, mỗi khi push lên `main`, Jenkins sẽ tự động build và deploy.

---

## Phần 7 — Troubleshooting

### ❌ `permission denied` khi Docker build trong Jenkins

```bash
docker exec -u root -it jenkins-dind bash
usermod -aG docker jenkins
exit
docker restart jenkins-dind
```

### ❌ `gcloud: command not found`

Kiểm tra `GCLOUD_PATH` trong `Jenkinsfile`:

```bash
docker exec -it jenkins-dind bash
which gcloud
# Nếu ra kết quả, copy path đó vào GCLOUD_PATH
```

Thông thường: `/var/jenkins_home/google-cloud-sdk/bin` hoặc `/usr/lib/google-cloud-sdk/bin`.

### ❌ `Unauthorized` khi push lên GCR

```bash
docker exec -u root -it jenkins-dind bash
gcloud auth configure-docker --quiet
exit
```

### ❌ Cloud Run không nhận được model (model not found)

Model được train **trong Docker build** (trong Dockerfile). Nếu GCS credentials không có sẵn lúc build, training sẽ fail.

Giải pháp tạm thời: sử dụng model file có sẵn trong `artifacts/models/` nếu đã train local, copy vào image:

```dockerfile
# Thêm vào deploy/Dockerfile nếu không muốn train trong build
COPY artifacts/models/lgbm_model.pkl ./artifacts/models/lgbm_model.pkl
```

### ❌ `RESOURCE_EXHAUSTED` trên Cloud Run

Free tier có giới hạn memory (256MB). LightGBM có thể cần nhiều hơn. Tăng memory:

```bash
gcloud run services update hotel-prediction \
  --memory=512Mi \
  --region=us-central1
```

### ❌ Build quá chậm (>15 phút)

LightGBM training lần đầu cài dependencies lâu. Các lần sau cache layer Docker giúp nhanh hơn. Nếu vẫn chậm, tăng `n_jobs=-1` trong `model_params.yaml` và giảm `n_iter` xuống `1` để test.

---

## Chi phí ước tính (GCP)

| Dịch vụ | Free tier | Chi phí nếu vượt |
|---------|----------|-----------------|
| Cloud Run | 2M requests/tháng | $0.40/M requests |
| GCS Storage | 5 GB | $0.020/GB/tháng |
| Container Registry | — | $0.026/GB/tháng |
| Egress | 1 GB/tháng | $0.12/GB |

> Với traffic nhỏ (demo/học tập), chi phí thực tế **gần như $0/tháng**.

Xóa resources khi không dùng:

```bash
# Xóa Cloud Run service
gcloud run services delete hotel-prediction --region=us-central1

# Xóa GCR images
gcloud container images delete gcr.io/hotel-prediction-prod/hotel-prediction --force-delete-tags

# Xóa GCS bucket
gcloud storage rm -r gs://YOUR_BUCKET_NAME
```
