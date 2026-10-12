# Model: Data Pipeline and State of Health Estimation

This folder contains the data pipeline for the NASA lithium-ion battery aging dataset:
inspection, preprocessing into a per-cycle table, and degradation plots.

> All results in this folder come from **NASA laboratory data** (historical, 2008).
> They are not live sensor measurements and do not describe any other battery.

## 1. Data source

| Item | Value |
|---|---|
| Dataset | NASA PCoE "Battery Data Set" (cells B0005, B0006, B0007, B0018) |
| Repository | [NASA Prognostics Center of Excellence Data Set Repository](https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/) |
| Download | https://phm-datasets.s3.amazonaws.com/NASA/5.+Battery+Data+Set.zip |
| Citation | B. Saha and K. Goebel (2007). "Battery Data Set", NASA Prognostics Data Repository, NASA Ames Research Center, Moffett Field, CA. |

The raw `.mat` files are **not** stored in this repository. To reproduce:

1. Download the zip above and extract it (it contains further zip files).
2. Copy `B0005.mat`, `B0006.mat`, `B0007.mat`, `B0018.mat` and `README.txt`
   into `model/data/raw/`.

## 2. Test protocol (from the NASA README)

- Commercial Li-ion 18650 cells, tested at room temperature (files record 24 °C ambient).
- **Charge:** constant current 1.5 A until 4.2 V, then constant voltage until current drops to 20 mA.
- **Discharge:** constant current 2 A until the voltage falls to a cut-off that differs per cell:

  | Cell | Cut-off voltage (README) | Median minimum voltage measured |
  |---|---|---|
  | B0005 | 2.7 V | 2.660 V |
  | B0006 | 2.5 V | 2.429 V |
  | B0007 | 2.2 V | 2.102 V |
  | B0018 | 2.5 V | 2.415 V |

- **Impedance:** EIS sweep from 0.1 Hz to 5 kHz.
- **Stop criterion stated by NASA:** 30% fade in rated capacity (2 Ah → 1.4 Ah).

## 3. File structure (verified with `inspect_dataset.py`)

| Cell | Records | Charge | Discharge | Impedance |
|---|---|---|---|---|
| B0005 | 616 | 170 | 168 | 278 |
| B0006 | 616 | 170 | 168 | 278 |
| B0007 | 616 | 170 | 168 | 278 |
| B0018 | 319 | 134 | 132 | 53 |

Discharge measurement fields and units:

| Field | Unit | Meaning |
|---|---|---|
| `Voltage_measured` | V | Battery terminal voltage |
| `Current_measured` | A | Battery output current |
| `Temperature_measured` | °C | Battery temperature |
| `Current_load` | A | Current measured at the load |
| `Voltage_load` | V | Voltage measured at the load |
| `Time` | s | Time since the start of the cycle |
| `Capacity` | Ah | Discharge capacity (one value per cycle) |

## 4. How to run

From the project root, with the virtual environment active:

    python model/scripts/inspect_dataset.py --save
    python model/scripts/preprocess_data.py
    python model/scripts/plot_capacity.py

| Script | Output |
|---|---|
| `inspect_dataset.py` | `model/reports/inspection_report.txt` |
| `preprocess_data.py` | `model/data/processed/discharge_cycles.csv`, `model/reports/preprocessing_log.txt` |
| `plot_capacity.py` | three PNG figures in `model/reports/figures/` |

## 5. Preprocessing

One row per **discharge** cycle. A cycle is skipped (and logged) if a required field
is missing, its arrays have different lengths, it has fewer than 10 samples, it
contains NaN values, or its capacity is not a positive number.

Result on the real data: **636 discharge cycles kept, 0 skipped.**

Main output columns:

| Column | Description |
|---|---|
| `battery_id`, `discharge_cycle` | Cell and 1-based discharge counter |
| `start_time`, `ambient_temperature_c` | Cycle start and ambient temperature |
| `capacity_ah` | Discharge capacity reported by NASA |
| `duration_s` | Length of the recorded discharge cycle |
| `voltage_start_v`, `voltage_min_v`, `voltage_mean_v` | Voltage summary |
| `current_mean_a` | Mean of `Current_measured` |
| `temperature_*` | Start, max, mean, rise, and time to max temperature |
| `re_ohm_last`, `rct_ohm_last` | Most recent impedance values before this discharge (empty before the first impedance test) |
| `soh_pct` | Capacity / first measured capacity of the same cell × 100 |
| `soh_rated_pct` | Capacity / 2.0 Ah rated capacity × 100 |

### State of Health definition

    soh_pct       = capacity_ah / first valid discharge capacity of the same cell × 100
    soh_rated_pct = capacity_ah / 2.0 Ah × 100

These are **operational definitions for this project**, not a universal battery-health
standard. `soh_pct` is used for the figures because the cells started at different
capacities (1.855–2.035 Ah).

## 6. Results

| Cell | Discharge cycles | First capacity | Last capacity | Lowest `soh_pct` | Reached 1.4 Ah? |
|---|---|---|---|---|---|
| B0005 | 168 | 1.856 Ah | 1.325 Ah | 69.3% | Yes |
| B0006 | 168 | 2.035 Ah | 1.186 Ah | 56.7% | Yes |
| B0007 | 168 | 1.891 Ah | 1.432 Ah | 74.1% | **No** (lowest ≈ 1.400 Ah) |
| B0018 | 132 | 1.855 Ah | 1.341 Ah | 72.3% | Yes |

![Discharge capacity per cycle](../docs/figures/capacity_vs_cycle.png)

![State of Health per cycle](../docs/figures/soh_vs_cycle.png)

![B0005 discharge voltage curves](../docs/figures/discharge_curves_B0005.png)

## 7. Observations and limitations

1. **Different cut-off voltages.** Each cell was discharged to a different voltage,
   so the four cells are not identical experiments. This matters when a model trained
   on some cells is tested on another.
2. **Capacity regeneration.** Capacity sometimes jumps up for a few cycles (for example
   near cycles 20, 30, 47, 89, 120 and 150), most likely after rest periods. These points
   are kept, not removed as outliers. It means a cell can drop below a threshold and
   briefly rise above it again.
3. **Rest period inside the discharge record.** After the cut-off voltage is reached,
   the voltage recovers while recording continues. `duration_s` and `voltage_mean_v`
   therefore include a short rest period.
4. **Target leakage warning.** With constant-current discharge, `duration_s` is almost a
   direct function of capacity. It must not be used as an input when predicting
   capacity-based SoH.
5. **B0007 never reached NASA's 1.4 Ah end-of-life level** in the recorded data, although
   the README says the experiments stopped at that criterion. Its full remaining-useful-life
   label under that definition is therefore unknown and must not be invented.
6. **README vs. file differences.** The NASA README lists discharge fields as
   `Current_charge` / `Voltage_charge`, but the files contain `Current_load` /
   `Voltage_load`. The README also says capacity is "for discharge till 2.7 V", while the
   cut-off differs per cell; this could not be verified from the files.
7. **Sign convention.** `Current_load` is positive for B0018 and negative for the other
   cells, so the pipeline uses `Current_measured`.
8. **Small sample.** Four cells of one type, tested in one lab under room-temperature
   conditions. Results do not generalize to other chemistries, cell designs or real-world
   operating conditions.
9. **Missing impedance values.** `re_ohm_last` / `rct_ohm_last` are empty for 57 early
   discharge rows (about the first 19 discharges of B0005, B0006 and B0007), because no
   impedance test had been run yet.

   ---

# Stage 2: State of Health estimation (v0.2.0)

## 8. Prediction task

> Given only the **first 10 minutes** of a 2 A constant-current discharge, estimate the
> cell's capacity-based State of Health.

- **Target:** `soh_rated_pct` = discharge capacity / 2.0 Ah rated capacity × 100.
  The rated capacity is used (instead of each cell's first capacity) so that the same
  feature values mean the same absolute capacity for every cell.
- **Why 10 minutes:** capacity is measured by discharging to the cut-off voltage, so any
  feature describing the whole discharge (duration, time of peak temperature, minimum
  voltage) would leak the target. Every discharge lasts more than 30 minutes, so the
  10-minute window never reaches the cut-off and is unaffected by the different cut-off
  voltages of the four cells.

## 9. Features (`build_features.py`)

| Feature | Meaning |
|---|---|
| `v_start_v` | Voltage at the start of the discharge |
| `v_drop_30s_v` | Voltage drop in the first 30 s (internal-resistance effect) |
| `v_at_60s_v`, `v_at_300s_v`, `v_at_600s_v` | Voltage at 1, 5 and 10 minutes |
| `v_slope_60_600_mv_per_min` | Voltage slope between 1 and 10 minutes |
| `temp_start_c` | Temperature at the start |
| `temp_rise_600s_c` | Temperature increase during the first 10 minutes |

Excluded on purpose: `capacity_ah`, `soh_pct`, `duration_s`, `time_to_temp_max_s`, and all
whole-discharge summaries (target leakage); `re_ohm_last` / `rct_ohm_last` (missing for
57 early rows; possible future improvement).

Correlation with the target (all cells pooled): slope +0.956, `v_at_600s_v` +0.907,
`v_drop_30s_v` −0.854, `temp_rise_600s_c` −0.577, `v_start_v` +0.154, `temp_start_c` +0.095.

## 10. Evaluation method (`train_soh_model.py`)

**Leave-one-battery-out (LOBO):** train on three cells, test on the fourth, repeat for
every cell. The test cell is never seen during training. A random row split was not used,
because cycles of the same cell would appear in both training and test data.

| Model | Description |
|---|---|
| `mean_baseline` | Always predicts the mean SoH of the training cells |
| `linear_regression` | Standardized features + ordinary least squares |
| `random_forest` | 300 trees, `min_samples_leaf=2`, `random_state=42` |

## 11. Results

MAE per held-out cell (SoH percentage points of rated capacity):

| Held-out cell | Mean baseline | Linear Regression | Random Forest | Random Forest R² |
|---|---|---|---|---|
| B0005 | 8.56 | 2.84 | **1.65** | 0.956 |
| B0006 | 11.35 | 6.14 | **4.42** | 0.833 |
| B0007 | 7.43 | 2.24 | **1.53** | 0.945 |
| B0018 | 7.03 | 2.76 | **1.05** | 0.973 |

All held-out predictions pooled:

| Model | MAE | RMSE | R² |
|---|---|---|---|
| Mean baseline | 8.682 | 10.085 | −0.031 |
| Linear Regression | 3.536 | 4.875 | 0.759 |
| **Random Forest** | **2.225** | **3.047** | **0.906** |

An MAE of 2.2 percentage points corresponds to about 0.045 Ah on a 2.0 Ah rated cell.

![Leave-one-battery-out predictions](../docs/figures/lobo_predictions.png)

![Random Forest parity plot](../docs/figures/lobo_parity.png)

## 12. Findings

1. **Both models clearly beat the baseline**, and Random Forest beats Linear Regression on
   every held-out cell.
2. **B0006 is the hardest cell.** 49 of its 168 targets (27 below, 22 above) lie outside the
   SoH range of the other three cells. Random Forest cannot predict outside its training
   range: its B0006 predictions flatten at about 65% (the lowest training value) and stay
   below about 92% at the start, while the true SoH reaches about 58% and starts near 102%.
3. **Linear Regression extrapolates, but badly** on B0006: late-life predictions fall far
   below the true values (to about 40%). Extrapolation is unreliable for both models.
   Range coverage explains a large part of the B0006 error, but cell-to-cell differences
   may also contribute; this was not isolated.
4. **Capacity regeneration is tracked.** The capacity jump near cycle 90 also appears in
   the predictions, although the model never sees capacity. The early-discharge features
   reflect the cell's state, not only its cycle count.

## 13. Saved model

`train_soh_model.py` retrains the Random Forest on all four cells and saves:

- `model/artifacts/soh_model.joblib` (not committed; recreate by running the script)
- `model/artifacts/soh_model_metadata.json` (feature list, target, window length,
  LOBO metrics, validity statement)

The model is valid **only** for inputs computed the same way (first 600 s of a 2 A
constant-current discharge) on cells similar to the NASA 18650 cells at about 24 °C.
It has **not** been validated on any other battery, current or temperature, and must not
be applied to live sensor data that does not match these conditions.

## 14. Remaining Useful Life (RUL): not included in v0.2.0

A RUL model was deliberately not built yet:

- Only three cells (B0005, B0006, B0018) reach NASA's 1.4 Ah end-of-life level. B0007 does
  not, so its RUL label is unknown (censored) and must not be invented.
- Three run-to-failure cells are too few for a meaningful battery-wise RUL evaluation.
- Capacity regeneration makes "end of life" ambiguous (first crossing vs. permanent
  crossing of the threshold); a definition must be chosen and justified first.

A future RUL extension would need an explicit EOL definition, handling of censored cells,
and preferably additional run-to-failure data.

## 15. Stage 2 limitations

- Four cells of one type, one lab, one discharge current, room temperature only.
- LOBO results with four folds have high uncertainty; one unusual cell (B0006) strongly
  affects the averages.
- No hyperparameter tuning was done; default-style settings were chosen in advance.
- Results describe NASA laboratory data only and are not a claim about commercial
  batteries or real-world operating conditions.

## 16. How to run Stage 2

    python model/scripts/build_features.py
    python model/scripts/train_soh_model.py
    python model/scripts/evaluate_model.py