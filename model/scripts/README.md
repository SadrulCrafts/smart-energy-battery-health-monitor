# Smart Energy & Battery Health Monitoring System

An end-to-end prototype combining Machine Learning, IoT sensors, a FastAPI backend,
and a Next.js dashboard for battery health monitoring.

> Status: under development (Stage 1: dataset pipeline)

## Dataset
NASA PCoE Li-ion Battery Aging Data (B0005, B0006, B0007, B0018).
Download: https://phm-datasets.s3.amazonaws.com/NASA/5.+Battery+Data+Set.zip
Raw files are **not** included in this repository; place the extracted `.mat` files in `model/data/raw/`.

Citation: B. Saha and K. Goebel (2007). "Battery Data Set", NASA Prognostics Data Repository,
NASA Ames Research Center, Moffett Field, CA.

## Setup (Windows)
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    python model/scripts/verify_environment.py