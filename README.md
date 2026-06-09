# Hotel Reservations Prediction 🏨

Dự đoán khả năng hủy đặt phòng khách sạn sử dụng **LightGBM**, được theo dõi bởi **MLflow**, phục vụ qua **Flask**, và triển khai lên **Google Cloud Run** thông qua **Jenkins CI/CD**.

---

```
Raw CSV (GCS)  →  Training Pipeline  →  LightGBM Model (.pkl)
                                              ↓
                              Flask App  →  Prediction API
                                              ↓
                         Jenkins CI/CD  →  Google Cloud Run
```

---

## Documentation

| Tài liệu | Mô tả |
|----------|-------|
| [Installation](docs/installation.md) | Cài đặt môi trường, dependencies, credentials |
| [Quick Start](docs/quickstart.md) | Chạy thử local trong < 10 phút |
| [Training Guide](docs/training.md) | Pipeline ML, config, MLflow tracking |
| [Architecture](docs/architecture.md) | Cấu trúc project, thiết kế, data flow |
| [Deployment Guide](docs/deployment.md) | Full A–Z: GCP + Jenkins + Cloud Run |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| ML Model | LightGBM + scikit-learn |
| Experiment Tracking | MLflow |
| Serving | Flask + Gunicorn |
| Containerisation | Docker (multi-stage, Python 3.11) |
| CI/CD | Jenkins |
| Cloud | GCP Cloud Run + GCS |
| Data Balancing | SMOTE (imbalanced-learn) |

---

## License

MIT — see [LICENSE](LICENSE).
