"""
Anomaly Detection Results - Storage and Access Guide
=====================================================
This script shows where anomaly warnings are stored and how to access them
"""

import sys
sys.path.append('/Users/sahin/Desktop/project/flight-ad-main/examples')

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

print("=" * 80)
print("ANOMALY DETECTION RESULTS - WHERE ARE THEY STORED?")
print("=" * 80)

# Run the pipeline
print("\n1. Running anomaly detection pipeline...")
data_bindings = load_dashlink_bindings()
binder = DataBinder(data_bindings)

wrangling_steps = [
    ('preprocess_flight', preprocess),
    ('resample_dataframe', resample),
    ('change_col', change_col),
    ('select_col', select)
]
wrangler = DataWrangler(wrangling_steps, memorize='change_col')

learning_steps = {
    'preprocessing': [
        ('reshaper', FunctionTransformer(reshape_df_interspersed)),
        ('scaler', StandardScaler()),
        ('pca', PCA())
    ],
    'training': [
        ('dbscan', DBSCAN())
    ]
}
learner = StatisticalLearner(learning_steps, record='pca')

ad_pipeline = AnomalyDetectionPipeline(binder, wrangler, learner)
ad_pipeline.fit()

print("✓ Pipeline completed!")

print("\n" + "=" * 80)
print("WHERE ANOMALY RESULTS ARE STORED")
print("=" * 80)

print("\n📍 LOCATION 1: learner.pipeline['dbscan'].labels_")
print("   This is the PRIMARY storage location for anomaly warnings")
print("   Type: numpy array")
print("   Values: -1 = ANOMALY, 0,1,2... = normal cluster IDs")

labels = learner.pipeline['dbscan'].labels_
print(f"\n   Array length: {len(labels)}")
print(f"   Unique labels: {sorted(set(labels))}")
print(f"   Sample labels: {labels[:20]}")

print("\n\n📍 LOCATION 2: learner.pipeline['dbscan'] (DBSCAN object)")
print("   The trained DBSCAN model stores all clustering information:")

dbscan_model = learner.pipeline['dbscan']
print(f"   - labels_: {type(dbscan_model.labels_)}")
print(f"   - core_sample_indices_: {len(dbscan_model.core_sample_indices_)} core samples")
print(f"   - components_: shape {dbscan_model.components_.shape}")
print(f"   - epsilon used: {dbscan_model.eps:.6f}")

print("\n\n📍 LOCATION 3: learner.partial_data['pca']")
print("   Stores the PCA-transformed data (10 dimensions)")
print("   Useful for visualization and further analysis")

pca_data = learner.partial_data['pca']
print(f"   Type: {type(pca_data)}")
print(f"   Shape: {len(pca_data)} flights × {len(pca_data[0])} dimensions")

print("\n" + "=" * 80)
print("EXTRACTING ANOMALY INFORMATION")
print("=" * 80)

# Get clustering info
labels, n_clusters, n_noise = clustering_info(learner.pipeline['dbscan'])
avg_silhouette, sample_silhouette = silhouette(learner.partial_data['pca'], labels)

# Find anomalous flights
flight_ids = list(data_bindings.keys())
anomaly_indices = np.where(labels == -1)[0]
anomalous_flights = [flight_ids[i] for i in anomaly_indices]

print(f"\n🚨 ANOMALOUS FLIGHTS DETECTED: {len(anomalous_flights)}")
print("\nFlight IDs of anomalies:")
for i, flight_id in enumerate(anomalous_flights, 1):
    sil_score = sample_silhouette[anomaly_indices[i-1]] if len(sample_silhouette) > 0 else 0
    print(f"   {i:2d}. Flight {flight_id} (silhouette: {sil_score:.4f})")

print("\n" + "=" * 80)
print("CREATING ANOMALY REPORT DATAFRAME")
print("=" * 80)

# Create comprehensive report
anomaly_report = pd.DataFrame({
    'flight_id': flight_ids,
    'cluster_label': labels,
    'is_anomaly': labels == -1,
    'silhouette_score': sample_silhouette if len(sample_silhouette) > 0 else [0] * len(labels)
})

# Add severity ranking (lower silhouette = more anomalous)
anomaly_report['anomaly_severity'] = anomaly_report.apply(
    lambda x: -x['silhouette_score'] if x['is_anomaly'] else 0, axis=1
)

print("\nAnomaly Report Preview:")
print(anomaly_report.head(10))

print("\n\nAnomaly Summary Statistics:")
print(anomaly_report[anomaly_report['is_anomaly']].describe())

# Save to CSV
output_file = '/Users/sahin/Desktop/project/flight-ad-main/anomaly_report.csv'
anomaly_report.to_csv(output_file, index=False)
print(f"\n✅ Full report saved to: {output_file}")

# Save just anomalies
anomaly_only_file = '/Users/sahin/Desktop/project/flight-ad-main/anomalies_only.csv'
anomaly_report[anomaly_report['is_anomaly']].to_csv(anomaly_only_file, index=False)
print(f"✅ Anomaly-only report saved to: {anomaly_only_file}")

print("\n" + "=" * 80)
print("FAULT ISOLATION + CONFIDENCE DASHBOARD")
print("=" * 80)

dashboard_df, per_flight_scores = build_confidence_dashboard(
    binder,
    wrangler,
    labels,
    flight_ids=flight_ids,
    anomaly_label=-1,
    top_n=3
)

dashboard_file = '/Users/sahin/Desktop/project/flight-ad-main/fault_isolation_dashboard.csv'
dashboard_df.to_csv(dashboard_file, index=False)
print(f"✅ Fault isolation dashboard saved to: {dashboard_file}")

print("\nTop sensor contributors for anomalies:")
for idx in anomaly_indices:
    top_sensors = isolate_faults(per_flight_scores[idx], top_n=3)
    top_desc = ", ".join([f"{s}:{score:.3f}" for s, score in top_sensors])
    print(f"   Flight {flight_ids[idx]} -> {top_desc}")

print("\n" + "=" * 80)
print("HOW TO ACCESS RESULTS IN YOUR CODE")
print("=" * 80)

code_example = '''
# After running ad_pipeline.fit():

# Method 1: Get labels directly
labels = learner.pipeline['dbscan'].labels_
anomaly_mask = labels == -1
anomalous_indices = np.where(anomaly_mask)[0]

# Method 2: Use reporting functions
from flight_ad.report import clustering_info, silhouette
labels, n_clusters, n_noise = clustering_info(learner.pipeline['dbscan'])
avg_sil, sample_sil = silhouette(learner.partial_data['pca'], labels)

# Method 3: Get flight IDs of anomalies
flight_ids = list(binder.bindings.keys())
anomalous_flights = [flight_ids[i] for i in anomalous_indices]

# Method 4: Create custom report
import pandas as pd
report = pd.DataFrame({
    'flight_id': flight_ids,
    'is_anomaly': labels == -1,
    'cluster': labels,
    'silhouette': sample_sil
})

# Filter anomalies
anomalies = report[report['is_anomaly']]

# Save to file
anomalies.to_csv('anomaly_warnings.csv')
'''

print(code_example)

print("\n" + "=" * 80)
print("SUMMARY: ANOMALY STORAGE LOCATIONS")
print("=" * 80)

summary = """
┌────────────────────────────────────────────────────────────────────────┐
│ STORAGE LOCATION                      │ WHAT IT CONTAINS               │
├────────────────────────────────────────────────────────────────────────┤
│ learner.pipeline['dbscan'].labels_    │ Cluster labels (-1=anomaly)    │
│ learner.pipeline['dbscan'].eps        │ Epsilon parameter used         │
│ learner.pipeline['dbscan'].components_│ Core sample features           │
│ learner.partial_data['pca']           │ PCA-transformed data           │
│ binder.bindings.keys()                │ Flight IDs                     │
│ wrangler.results                      │ Intermediate wrangling results │
└────────────────────────────────────────────────────────────────────────┘

🎯 PRIMARY ACCESS PATTERN:
   1. Get labels: learner.pipeline['dbscan'].labels_
   2. Find anomalies: np.where(labels == -1)[0]
   3. Get flight IDs: list(binder.bindings.keys())
   4. Match indices to IDs: [flight_ids[i] for i in anomaly_indices]
   
💾 PERSISTENCE:
   - Results stored in memory only (not automatically saved)
   - Must export to CSV/JSON for permanent storage
   - Can pickle the entire pipeline for reuse
"""

print(summary)

print("\n" + "=" * 80)
print("COMPLETE ✓")
print("=" * 80)
