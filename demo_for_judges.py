"""
LIVE DEMO FOR HACKATHON JUDGES
================================
Clean, impressive demonstration of flight anomaly detection
Run this during your presentation!
"""

import sys
sys.path.append('/Users/sahin/Desktop/project/flight-ad-main/examples')
import time
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
import pandas as pd
import numpy as np

def print_header(text):
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80)

def print_step(number, text):
    print(f"\n▶ STEP {number}: {text}")
    print("-" * 80)

# Title
print("\n\n")
print("╔" + "=" * 78 + "╗")
print("║" + " " * 20 + "FLIGHT ANOMALY DETECTION SYSTEM" + " " * 27 + "║")
print("║" + " " * 25 + "Live Demonstration" + " " * 32 + "║")
print("╚" + "=" * 78 + "╝")

time.sleep(1)

# Step 1: Data Loading
print_step(1, "LOADING NASA DASHLINK FLIGHT DATA")
print("Source: NASA's DASHlink - Real commercial flight recordings")

start_time = time.time()
data_bindings = load_dashlink_bindings()
binder = DataBinder(data_bindings)
load_time = time.time() - start_time

print(f"\n✓ Successfully loaded {len(data_bindings)} flight recordings")
print(f"✓ Load time: {load_time:.2f} seconds")

# Show sample flight info
sample_flight_id = list(data_bindings.keys())[0]
sample_data = binder.retrieve_data(sample_flight_id)
print(f"\n📊 Sample Flight: {sample_flight_id}")
print(f"   • Data points: {sample_data.shape[0]:,}")
print(f"   • Sensor parameters: {sample_data.shape[1]}")
print(f"   • Flight duration: {sample_data['time'].max():.0f} seconds ({sample_data['time'].max()/60:.1f} minutes)")

time.sleep(2)

# Step 2: Pipeline Configuration
print_step(2, "CONFIGURING AI PIPELINE")

print("\n🔧 Data Wrangling Pipeline:")
wrangling_steps = [
    ('preprocess_flight', preprocess),
    ('resample_dataframe', resample),
    ('change_col', change_col),
    ('select_col', select)
]
wrangler = DataWrangler(wrangling_steps, memorize='change_col')

for i, (name, _) in enumerate(wrangling_steps, 1):
    print(f"   {i}. {name.replace('_', ' ').title()}")

print("\n🤖 Machine Learning Pipeline:")
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

print("   Preprocessing:")
for name, step in learning_steps['preprocessing']:
    print(f"      • {type(step).__name__}")
print("   Anomaly Detection:")
for name, step in learning_steps['training']:
    print(f"      • {type(step).__name__} (Adaptive - Auto-tuning)")

time.sleep(1)

# Step 3: Running Detection
print_step(3, "RUNNING ANOMALY DETECTION")
print("Processing all 400 flights through AI pipeline...")
print("(Watch the progress bar below)")

start_time = time.time()
ad_pipeline = AnomalyDetectionPipeline(binder, wrangler, learner)
ad_pipeline.fit()
processing_time = time.time() - start_time

print(f"\n✓ Processing complete!")
print(f"✓ Total time: {processing_time:.2f} seconds")
print(f"✓ Speed: {len(data_bindings)/processing_time:.1f} flights/second")

time.sleep(1)

# Step 4: Analyzing Results
print_step(4, "ANALYZING RESULTS")

labels, n_clusters, n_noise = clustering_info(learner.pipeline['dbscan'])
avg_silhouette, sample_silhouette = silhouette(learner.partial_data['pca'], labels)

print("\n📈 Clustering Metrics:")
print(f"   • Total flights analyzed: {len(labels)}")
print(f"   • Normal flight patterns: {n_clusters}")
print(f"   • Normal flights: {len(labels) - n_noise} ({(len(labels) - n_noise)/len(labels)*100:.1f}%)")
print(f"   • Anomalous flights: {n_noise} ({n_noise/len(labels)*100:.2f}%)")
print(f"   • Cluster quality (silhouette): {avg_silhouette:.4f}")
print(f"   • Epsilon (auto-calculated): {learner.pipeline['dbscan'].eps:.6f}")

time.sleep(2)

# Step 5: Identifying Anomalies
print_step(5, "IDENTIFYING DANGEROUS FLIGHTS")

flight_ids = list(data_bindings.keys())
anomaly_indices = np.where(labels == -1)[0]
anomalous_flights = [flight_ids[i] for i in anomaly_indices]

print(f"\n🚨 {len(anomalous_flights)} ANOMALOUS FLIGHTS DETECTED:")
print("\n" + "-" * 80)
print(f"{'Rank':<6} {'Flight ID':<20} {'Silhouette Score':<20} {'Severity':<15}")
print("-" * 80)

# Sort by silhouette score (most anomalous first)
anomaly_data = []
for idx in anomaly_indices:
    anomaly_data.append({
        'flight_id': flight_ids[idx],
        'silhouette': sample_silhouette[idx],
        'severity': 'HIGH' if sample_silhouette[idx] < -0.1 else 'MEDIUM' if sample_silhouette[idx] < 0.1 else 'LOW'
    })

anomaly_data.sort(key=lambda x: x['silhouette'])

for i, item in enumerate(anomaly_data[:10], 1):  # Show top 10
    print(f"{i:<6} {item['flight_id']:<20} {item['silhouette']:<20.4f} {item['severity']:<15}")

if len(anomaly_data) > 10:
    print(f"... and {len(anomaly_data) - 10} more")

time.sleep(1)

# Step 6: Creating Report
print_step(6, "GENERATING DETAILED REPORT")

# Create comprehensive report
anomaly_report = pd.DataFrame({
    'flight_id': flight_ids,
    'cluster_label': labels,
    'is_anomaly': labels == -1,
    'silhouette_score': sample_silhouette,
    'anomaly_severity': ['HIGH' if labels[i] == -1 and sample_silhouette[i] < -0.1 
                          else 'MEDIUM' if labels[i] == -1 and sample_silhouette[i] < 0.1
                          else 'LOW' if labels[i] == -1 
                          else 'NORMAL' 
                          for i in range(len(labels))]
})

# Save reports
full_report_file = '/Users/sahin/Desktop/project/flight-ad-main/anomaly_report.csv'
anomaly_only_file = '/Users/sahin/Desktop/project/flight-ad-main/anomalies_only.csv'

anomaly_report.to_csv(full_report_file, index=False)
anomaly_report[anomaly_report['is_anomaly']].to_csv(anomaly_only_file, index=False)

print(f"\n✅ Full report saved: anomaly_report.csv")
print(f"✅ Anomaly list saved: anomalies_only.csv")

# Summary statistics
print("\n📊 Report Statistics:")
print(f"   • Total records: {len(anomaly_report)}")
print(f"   • Anomalies flagged: {anomaly_report['is_anomaly'].sum()}")
print(f"   • High severity: {(anomaly_report['anomaly_severity'] == 'HIGH').sum()}")
print(f"   • Medium severity: {(anomaly_report['anomaly_severity'] == 'MEDIUM').sum()}")
print(f"   • Low severity: {(anomaly_report['anomaly_severity'] == 'LOW').sum()}")

time.sleep(1)

# Final Summary
print_header("DEMONSTRATION COMPLETE")

print("\n🎯 KEY RESULTS:")
print(f"   ✓ Processed {len(data_bindings)} flights in {processing_time:.1f} seconds")
print(f"   ✓ Detected {n_noise} anomalous flights ({n_noise/len(labels)*100:.2f}% rate)")
print(f"   ✓ Zero manual tuning required (epsilon auto-calculated)")
print(f"   ✓ Production-ready performance: {len(data_bindings)/processing_time:.1f} flights/second")

print("\n💼 BUSINESS IMPACT:")
print(f"   • Manual analysis time saved: ~{len(data_bindings) * 30} minutes → {processing_time:.0f} seconds")
print(f"   • Actionable insights: {n_noise} flights require expert review")
print(f"   • Scalability: Can process {int(len(data_bindings)/processing_time * 3600):,} flights/hour")

print("\n📁 OUTPUT FILES:")
print(f"   • anomaly_report.csv - Full dataset with labels")
print(f"   • anomalies_only.csv - Just the {n_noise} flagged flights")

print("\n🚀 NEXT STEPS:")
print("   1. Review flagged flights with aviation experts")
print("   2. Integrate with airline maintenance systems")
print("   3. Deploy for real-time monitoring")

print("\n" + "=" * 80)
print("  Thank you for watching! Questions?")
print("=" * 80 + "\n")

# Print where to access results
print("💡 Access Results:")
print(f"   Python: labels = learner.pipeline['dbscan'].labels_")
print(f"   CSV: cat anomalies_only.csv")
print(f"   Full report: open anomaly_report.csv")
