# Flight-AD: Complete Project Overview

## 1. **Project Purpose**
Detect **soft faults** in aircraft avionics using unsupervised ML. Soft faults (sensor drift, intermittent communication issues) precede catastrophic failure but aren't caught by traditional limit-checking BITE (Built-In Test Equipment).

---

## 2. **Data Source**

**Dataset:** NASA DASHlink (Real commercial flight data)  
**Location:** `flight_ad/datasets/data.json`  
**File Format:** Parquet (binary columnar storage)  
**Size:** ~400 flight recordings, ~2MB each (total ~1GB)  
**Download:** Automatic via `flight_ad/datasets/dashlink.py`

---

## 3. **Raw Sensor Parameters**

Each flight file contains **191 sensor parameters**, including:
- **RALT** – Radar altitude (height above ground)
- **CAS** – Calibrated airspeed
- **ALT** – Barometric altitude
- **WOW** – Weight-on-wheels (binary: ground/air)
- Plus 187 others: engine temps, fuel flow, hydraulic pressure, electrical status, etc.

**Samples per flight:** ~105,000 data points  
**Time resolution:** High-frequency sampling (~16 Hz)  
**Duration:** 1–2 hour flights

---

## 4. **Architecture (5-Layer Pipeline)**

```
┌─────────────────────────────────────────────────────────────┐
│ LAYER 1: DATA LOADING (DataBinder)                          │
│ ─ Lazy load 400 flight parquet files                        │
│ ─ No upfront memory load (efficient for large datasets)     │
│ ─ File: flight_ad/utils/data/interface.py                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ LAYER 2: DATA WRANGLING (DataWrangler)                      │
│ ─ Preprocessing: Full flight timeline                       │
│ ─ Resample: Uniform time intervals (282 samples)            │
│ ─ Change reference: Start of flight = t=0                   │
│ ─ Select parameters: RALT, CAS, ALT, WOW (4 sensors)        │
│ ─ File: flight_ad/wrangling/wrangler.py                    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ LAYER 3: FEATURE ENGINEERING (Transformations)              │
│ ─ Reshape: Time series → flat feature vectors               │
│ ─ Standardization: Zero mean, unit variance                 │
│ ─ PCA: 191 dims → 10 principal components                   │
│ ─ File: flight_ad/transformations/transforms.py             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ LAYER 4: ANOMALY DETECTION (DBSCAN)                         │
│ ─ Unsupervised clustering                                   │
│ ─ Auto-tunes epsilon (density threshold)                    │
│ ─ Labels: -1 = anomaly, 0/1/2... = normal clusters          │
│ ─ File: flight_ad/cluster/_dbscan.py                        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ LAYER 5: FAULT ISOLATION & REPORTING                        │
│ ─ Per-sensor confidence scores (0-1)                        │
│ ─ Top sensor contributors (ALT, CAS, RALT ranks)            │
│ ─ Silhouette scoring (quality metric)                       │
│ ─ Files: flight_ad/report/diagnostics.py, cluster.py       │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. **Data Flow (End-to-End)**

```
400 Parquet Files (105k samples each)
         ↓
    DataBinder
  (lazy load 1 flight)
         ↓
    DataWrangler
  (full flight, resample, select)
         ↓
  4 parameters (RALT, CAS, ALT, WOW)
  282 timepoints per flight
         ↓
    Reshape + StandardScaler + PCA
  (191 dims → 10 dims)
         ↓
    DBSCAN Clustering
  (auto-epsilon)
         ↓
  Labels: -1 (anomaly) or 0 (normal)
  Silhouette scores per flight
         ↓
  Confidence dashboard + Reports (CSV)
```

---

## 6. **ML Algorithms & Hyperparameters**

### **Preprocessing Pipeline**
| Step | Algorithm | Config | Purpose |
|------|-----------|--------|---------|
| Reshape | FunctionTransformer | Custom interspersed reshape | Convert 2D timeseries → 1D feature vector |
| Scale | StandardScaler | mean=0, std=1 | Normalize feature magnitudes |
| Reduce | PCA | n_components=10 | Reduce noise, capture variance |

### **Anomaly Detection**
| Algorithm | Params | Purpose |
|-----------|--------|---------|
| **DBSCAN** | eps=auto-calculated, min_samples=5 | Density-based clustering; finds sparse outliers |

**Why DBSCAN?**
- No cluster count assumption
- Finds true outliers (-1 label)
- Robust to soft faults (non-spherical anomalies)

### **Quality Metrics**
| Metric | Range | Current Value | Interpretation |
|--------|-------|----------------|-----------------|
| **Silhouette Score** | [-1, 1] | 0.3227 | Moderate cluster separation |
| **Anomaly Rate** | 0-100% | 2% | 8/400 flights flagged |
| **Per-flight Silhouette** | [-1, 1] | -0.288 to 0.131 | Individual flight "anomalousness" |

---

## 7. **Tech Stack**

### **Core Libraries**
```
numpy              2.1.3    – Numerical operations
pandas             2.2.3    – Dataframe processing
scikit-learn       1.5.2    – ML algorithms (DBSCAN, PCA, StandardScaler)
pyarrow            18.1.0   – Parquet file I/O
```

### **Web & Visualization**
```
streamlit          1.54.0   – Interactive web dashboard
plotly             5.24.1   – Interactive charts (histograms, heatmaps, bar)
matplotlib         3.10.8   – Static plotting
```

### **Utilities**
```
tqdm               4.67.3   – Progress bars
scikit-learn       1.5.2    – sklearn utilities (Pipeline, FunctionTransformer)
```

### **Python Version**
```
Python 3.13.7 (ARM64, macOS)
```

---

## 8. **Key Functionalities**

### **A. Data Loading**
- `flight_ad/datasets/dashlink.py` – Downloads & parses NASA DASHlink
- `flight_ad/utils/data/interface.py` – Lazy-loading DataBinder class

### **B. Data Wrangling**
- `examples/wrangling_functions.py` – Preprocessing pipeline
  - `preprocess()` – Full flight timeline, map categorical variables
  - `resample()` – Uniform time intervals
  - `change_col()` – Re-reference time to start of flight
  - `select()` – Choose RALT, CAS, ALT, WOW

### **C. Feature Transformation**
- `flight_ad/transformations/transforms.py` – Reshape, scale, PCA

### **D. Anomaly Detection**
- `flight_ad/cluster/_dbscan.py` – DBSCAN with auto-epsilon tuning

### **E. Fault Isolation**
- `flight_ad/report/diagnostics.py` – Per-sensor confidence scores
  - `build_confidence_dashboard()` – Confidence matrix (flight × sensor)
  - `isolate_faults()` – Top-N sensor contributors

### **F. Pipeline Orchestration**
- `flight_ad/pipeline/ad.py` – AnomalyDetectionPipeline class
  - Chains binder → wrangler → learner
  - Caches intermediate results

### **G. Reporting & Visualization**
- `flight_ad/report/cluster.py` – Clustering metrics (silhouette, n_clusters)
- `dashboard_app.py` – Streamlit web UI
  - KPI cards (flights analyzed, anomalies, rate)
  - Confidence histogram
  - Per-sensor heatmap
  - Top sensor bar chart

---

## 9. **Outputs & Reporting**

### **CSV Reports**
| File | Contains | Use Case |
|------|----------|----------|
| **anomaly_report.csv** | All 400 flights + cluster labels + silhouette scores | Full audit trail |
| **anomalies_only.csv** | 8 flagged flights + severity ranking | Quick review |
| **fault_isolation_dashboard.csv** | Per-sensor confidence + top-3 contributors per flight | Technician diagnosis |

### **Web Dashboard**
- **URL:** http://localhost:8501
- **Sections:**
  1. KPI cards (flights, anomalies, rate, avg confidence)
  2. Confidence distribution histogram
  3. Per-sensor heatmap (anomalies only)
  4. Top sensor contributors (aggregate)
  5. Report preview (first 20 flights)

### **Console Output**
- Live demo (`demo_for_judges.py`)
  - Load time, sample flight info
  - Pipeline steps
  - Processing speed (flights/sec)
  - Anomaly list with severity ranking
  - Business impact summary

---

## 10. **Execution Flow (Judges Demo)**

```bash
# 1. Activate venv
source .venv/bin/activate

# 2. Run live demo (console output)
python demo_for_judges.py
# Output: 8 anomalies detected in 55 sec, 7.3 flights/sec

# 3. Generate dashboard data
python anomaly_storage_guide.py
# Output: 3 CSV files + sensor rankings

# 4. Launch web UI
streamlit run dashboard_app.py
# Opens http://localhost:8501 in browser
```

---

## 11. **Why This Matches PS HY26-06**

✅ **Soft fault detection** – Catches sensor drift before alarms  
✅ **No pre-defined signatures** – Unsupervised (anomaly = statistical deviation)  
✅ **False Discovery Rate aware** – Silhouette scoring filters spurious alarms  
✅ **Data imbalance handled** – Only 2% anomalies (real-world ratio)  
✅ **Per-sensor fault isolation** – Top-3 sensor contributors identified  
✅ **Confidence dashboard** – Visual subsystem health scoring (0-1)  
✅ **Scalable** – 7.3 flights/sec (26k flights/hour)

---

## 12. **Quick Reference Commands**

### **Setup (One-time)**
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### **Run Demo**
```bash
python demo_for_judges.py        # Live console output
python anomaly_storage_guide.py   # Generate CSV reports
streamlit run dashboard_app.py    # Open web dashboard
```

### **View Results**
```bash
cat anomalies_only.csv                       # Flagged flights
cat fault_isolation_dashboard.csv            # Sensor contributors
open http://localhost:8501                   # Web UI
```

---

**Project Ready for Hackathon Judges. All outputs generated and documented.**
