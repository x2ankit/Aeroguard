"""
Aeroguard: Pipeline Demo
========================
Demonstrates the end-to-end anomaly detection pipeline on the NASA DASHlink
dataset.  Results are saved to ``outputs/`` and printed to the console.

Usage
-----
    python scripts/run_pipeline.py

Prerequisites
-------------
The NASA DASHlink dataset must be present in ``flight_ad/datasets/dashlink_flights/``.
Run with ``download=True`` on the first call to ``load_dashlink_bindings`` to
fetch it automatically, or see the README for manual download instructions.
"""

import sys
import time
from pathlib import Path
import numpy as np
import pandas as pd

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
from flight_ad.report import clustering_info, silhouette

OUTPUT_DIR = REPO_ROOT / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)


def separator(title=""):
    width = 72
    if title:
        print(f"\n{'-' * 4} {title} {'-' * (width - len(title) - 6)}")
    else:
        print("-" * width)


# ---------------------------------------------------------------------------
# Step 1: Load data
# ---------------------------------------------------------------------------
separator("Loading Data")
t0 = time.perf_counter()
data_bindings = load_dashlink_bindings()
binder = DataBinder(data_bindings)
print(f"Loaded {len(data_bindings)} flight recordings  ({time.perf_counter()-t0:.2f}s)")

sample_id = list(data_bindings.keys())[0]
sample = binder.retrieve_data(sample_id)
print(f"Sample flight  : {sample_id}")
print(f"  Shape        : {sample.shape[0]:,} samples × {sample.shape[1]} parameters")
print(f"  Duration     : {sample['time'].max()/60:.1f} minutes")

# ---------------------------------------------------------------------------
# Step 2: Configure pipeline
# ---------------------------------------------------------------------------
separator("Configuring Pipeline")
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

for name, _ in wrangling_steps:
    print(f"  Wrangling : {name}")
for stage, steps in learning_steps.items():
    for name, obj in steps:
        print(f"  ML [{stage:12s}] : {type(obj).__name__}")

# ---------------------------------------------------------------------------
# Step 3: Run
# ---------------------------------------------------------------------------
separator("Running Anomaly Detection")
t1 = time.perf_counter()
ad_pipeline = AnomalyDetectionPipeline(binder, wrangler, learner)
ad_pipeline.fit()
elapsed = time.perf_counter() - t1
print(f"Processing complete in {elapsed:.2f}s  ({len(data_bindings)/elapsed:.1f} flights/s)")

# ---------------------------------------------------------------------------
# Step 4: Results
# ---------------------------------------------------------------------------
separator("Results")
labels, n_clusters, n_noise = clustering_info(learner.pipeline['dbscan'])
avg_sil, sample_sil = silhouette(learner.partial_data['pca'], labels)

print(f"Flights analysed   : {len(labels)}")
print(f"Normal clusters    : {n_clusters}")
print(f"Normal flights     : {len(labels) - n_noise} ({(len(labels)-n_noise)/len(labels)*100:.1f}%)")
print(f"Anomalous flights  : {n_noise} ({n_noise/len(labels)*100:.2f}%)")
print(f"Silhouette score   : {avg_sil:.4f}")
print(f"Epsilon (auto)     : {learner.pipeline['dbscan'].eps:.6f}")

# ---------------------------------------------------------------------------
# Step 5: Anomaly list
# ---------------------------------------------------------------------------
flight_ids = list(data_bindings.keys())
anomaly_indices = np.where(labels == -1)[0]
sil_scores = list(sample_sil) if len(sample_sil) == len(labels) else [0.0] * len(labels)
anomaly_rows = [
    {'flight_id': flight_ids[i], 'silhouette': float(sil_scores[i])}
    for i in anomaly_indices
]
anomaly_rows.sort(key=lambda r: r['silhouette'])

separator(f"Anomalous Flights Detected: {len(anomaly_rows)}")
print(f"{'#':<4} {'Flight ID':<24} {'Silhouette':>12}")
print("-" * 44)
for rank, row in enumerate(anomaly_rows, 1):
    print(f"{rank:<4} {row['flight_id']:<24} {row['silhouette']:>12.4f}")

# ---------------------------------------------------------------------------
# Step 6: Save report
# ---------------------------------------------------------------------------
separator("Saving Report")
report = pd.DataFrame({
    'flight_id': flight_ids,
    'cluster_label': labels,
    'is_anomaly': labels == -1,
    'silhouette_score': sil_scores,
})
out_path = OUTPUT_DIR / 'anomaly_report.csv'
report.to_csv(out_path, index=False)
print(f"Report saved to {out_path}")
print(f"\nTo view the interactive dashboard, run:\n  streamlit run dashboard_app.py")