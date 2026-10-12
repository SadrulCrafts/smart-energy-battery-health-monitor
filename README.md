# Smart Energy & Battery Health Monitoring System

An end-to-end prototype combining Machine Learning, IoT sensors, a FastAPI backend,
and a Next.js dashboard for battery health monitoring.

> **Status:** v0.1.0 — dataset pipeline complete. Machine Learning model, backend,
> dashboard and hardware integration are planned for later versions.

![Discharge capacity per cycle](docs/figures/capacity_vs_cycle.png)

## Roadmap

| Version | Scope | Status |
|---|---|---|
| v0.1.0 | NASA dataset inspection, preprocessing and degradation plots | Done |
| v0.2.0 | State of Health prediction model with battery-wise evaluation | Planned |
| v0.3.0 | FastAPI backend, SQLite database and web dashboard (clearly labeled demo data) | Planned |
| v0.4.0 | Arduino sensor integration (INA219, DS18B20) | Planned |
| v1.0.0 | Integrated, tested and documented portfolio release | Planned |

## Dataset

NASA PCoE Li-ion Battery Aging Data (B0005, B0006, B0007, B0018).
Download: https://phm-datasets.s3.amazonaws.com/NASA/5.+Battery+Data+Set.zip

Raw files are **not** included in this repository. Place the extracted `.mat` files in
`model/data/raw/`. Details, assumptions and limitations: [model/README.md](model/README.md).

Citation: B. Saha and K. Goebel (2007). "Battery Data Set", NASA Prognostics Data Repository,
NASA Ames Research Center, Moffett Field, CA.

## Setup (Windows)

    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    python model/scripts/verify_environment.py

## Run the data pipeline

    python model/scripts/inspect_dataset.py --save
    python model/scripts/preprocess_data.py
    python model/scripts/plot_capacity.py

## License

Code: MIT License (see [LICENSE](LICENSE)). The NASA dataset is not redistributed here;
see the NASA repository for its terms of use.