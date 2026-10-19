"""
Aeroguard: Anomaly Detection Report Generator
=============================================
Runs the full anomaly detection pipeline on the NASA DASHlink dataset and
writes three CSV reports to an ``outputs/`` directory in the project root.

Usage
-----
    python scripts/generate_reports.py

Outputs
-------
outputs/fault_isolation_dashboard.csv
    Per-flight fault isolation dashboard with per-sensor confidence scores.
outputs/anomalies_only.csv
    Subset containing only the flights classified as anomalous.
outputs/anomaly_report.csv
    Full dataset report with cluster labels and silhouette scores.
"""

import sys
from pathlib import Path

# Ensure the examples directory is on the path so that wrangling_functions
# can be imported without requiring package installation.
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "examples"))

from flight_ad.datasets import load_dashlink_bindings
from flight_ad.utils.data import DataBinder
from flight_ad.wrangling import DataWrangler
from wrangling_functions import preprocess, change_col, resample, select
from flight_ad.transformations import reshape_df_interspersed
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from flight_ad.cluster import DBSCAN
from flight_ad.learn import FunctionTransformer, StatisticalLearner
from flight_ad.pipeline import AnomalyDetectionPipeline
from flight_ad.report import clustering_info, silhouette, build_confidence_dashboard, isolate_faults
import pandas as pd
import numpy as np

OUTPUT_DIR = REPO_ROOT / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# 1. Pipeline setup
# ---------------------------------------------------------------------------
print("Running anomaly detection pipeline...")
data_bindings = load_dashlink_bindings()
binder = DataBinder(data_bindings)

wrangling_steps = [
    ('preprocess_flight', preprocess),
    ('resample_dataframe', resample),
    ('change_col', change_col),
    ('select_col', select),
]
wrangler = DataWrangler(wrangling_steps, memorize='change_col')

learning_steps = {
    'preprocessing': [
        ('reshaper', FunctionTransformer(reshape_df_interspersed)),
        ('scaler', StandardScaler()),
        ('pca', PCA()),
    ],
    'training': [
        ('dbscan', DBSCAN()),
    ],
}
learner = StatisticalLearner(learning_steps, record='pca')

ad_pipeline = AnomalyDetectionPipeline(binder, wrangler, learner)
ad_pipeline.fit()
print("Pipeline complete.")

# ---------------------------------------------------------------------------
# 2. Extract results
# ---------------------------------------------------------------------------
labels, n_clusters, n_noise = clustering_info(learner.pipeline['dbscan'])
avg_silhouette, sample_silhouette = silhouette(learner.partial_data['pca'], labels)

flight_ids = list(data_bindings.keys())
anomaly_indices = np.where(labels == -1)[0]

print(f"\nFlights analysed : {len(labels)}")
print(f"Clusters found   : {n_clusters}")
print(f"Anomalies        : {n_noise} ({n_noise/len(labels)*100:.2f}%)")
print(f"Silhouette score : {avg_silhouette:.4f}")

# ---------------------------------------------------------------------------
# 3. Build and save reports
# ---------------------------------------------------------------------------
anomaly_report = pd.DataFrame({
    'flight_id': flight_ids,
    'cluster_label': labels,
    'is_anomaly': labels == -1,
    'silhouette_score': sample_silhouette if len(sample_silhouette) > 0 else [0] * len(labels),
    'anomaly_severity': [
        -sample_silhouette[i] if labels[i] == -1 else 0.0
        for i in range(len(labels))
    ],
})

report_path = OUTPUT_DIR / 'anomaly_report.csv'
anomaly_path = OUTPUT_DIR / 'anomalies_only.csv'

anomaly_report.to_csv(report_path, index=False)
anomaly_report[anomaly_report['is_anomaly']].to_csv(anomaly_path, index=False)
print(f"\nSaved: {report_path}")
print(f"Saved: {anomaly_path}")

# Fault isolation dashboard
dashboard_df, per_flight_scores = build_confidence_dashboard(
    binder, wrangler, labels,
    flight_ids=flight_ids,
    anomaly_label=-1,
    top_n=3,
)
dashboard_path = OUTPUT_DIR / 'fault_isolation_dashboard.csv'
dashboard_df.to_csv(dashboard_path, index=False)
print(f"Saved: {dashboard_path}")

# Per-anomaly fault isolation summary
print("\nTop sensor contributors per anomaly:")
for idx in anomaly_indices:
    top_sensors = isolate_faults(per_flight_scores[idx], top_n=3)
    desc = ", ".join(f"{s}:{score:.3f}" for s, score in top_sensors)
    print(f"  Flight {flight_ids[idx]} -> {desc}")