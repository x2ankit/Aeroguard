"""
Demonstration and Analysis of flight-ad Project
================================================
This script demonstrates the core functionality of the flight-ad package
and explains how each component works together.
"""

print("=" * 70)
print("FLIGHT-AD PROJECT ANALYSIS AND DEMONSTRATION")
print("=" * 70)

# ============================================================================
# STEP 1: Understanding the Data
# ============================================================================
print("\n1. LOADING FLIGHT DATA")
print("-" * 70)

from flight_ad.datasets import load_dashlink_bindings
from flight_ad.utils.data import DataBinder

# Load NASA DASHlink dataset bindings
# This contains 400 flights with sensor data
print("Loading NASA DASHlink flight dataset...")
data_bindings = load_dashlink_bindings()
binder = DataBinder(data_bindings)

print(f"✓ Loaded {len(data_bindings)} flight recordings")
print(f"✓ DataBinder manages lazy loading of flight data")

# Show a sample of what the data looks like
print("\nExamining first flight data structure...")
first_key = list(data_bindings.keys())[0]
sample_flight = binder.retrieve_data(first_key)
print(f"✓ Flight ID: {first_key}")
print(f"✓ Data shape: {sample_flight.shape}")
print(f"✓ Columns: {list(sample_flight.columns)}")
print(f"✓ Time range: {sample_flight['time'].min():.2f}s to {sample_flight['time'].max():.2f}s")

# ============================================================================
# STEP 2: Data Wrangling Pipeline
# ============================================================================
print("\n\n2. DATA WRANGLING PIPELINE")
print("-" * 70)

from flight_ad.wrangling import DataWrangler
import sys
sys.path.append('/Users/sahin/Desktop/project/flight-ad-main/examples')
from wrangling_functions import preprocess, change_col, resample, select

# Create a data wrangling pipeline
# Each step transforms the data sequentially
wrangling_steps = [
    ('preprocess_flight', preprocess),  # Extract relevant flight portion
    ('resample_dataframe', resample),   # Normalize time sampling
    ('change_col', change_col),         # Re-reference time column
    ('select_col', select)              # Select specific parameters
]
wrangler = DataWrangler(wrangling_steps, memorize='change_col')

print("Wrangling pipeline steps:")
for i, (name, func) in enumerate(wrangling_steps, 1):
    print(f"  {i}. {name}: {func.__doc__.strip() if func.__doc__ else 'Data transformation'}")

# Process a single flight to show transformation
print("\nApplying wrangling to sample flight...")
wrangled_flight = wrangler.compose(sample_flight)
print(f"✓ Original shape: {sample_flight.shape}")
print(f"✓ Wrangled shape: {wrangled_flight.shape}")
print(f"✓ Selected parameters: {list(wrangled_flight.columns)}")

# ============================================================================
# STEP 3: Feature Engineering & Machine Learning Pipeline
# ============================================================================
print("\n\n3. STATISTICAL LEARNING PIPELINE")
print("-" * 70)

from flight_ad.transformations import reshape_df_interspersed
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from flight_ad.cluster import DBSCAN
from flight_ad.learn import FunctionTransformer, StatisticalLearner

# The learning pipeline has two stages:
# 1. Preprocessing: reshape data, scale, and dimensionality reduction
# 2. Training: clustering to find anomalies

learning_steps = {
    'preprocessing': [
        ('reshaper', FunctionTransformer(reshape_df_interspersed)),
        ('scaler', StandardScaler()),
        ('pca', PCA(n_components=10))
    ],
    'training': [
        ('dbscan', DBSCAN(min_samples=5))
    ]
}
learner = StatisticalLearner(learning_steps, record='pca')

print("Preprocessing steps:")
for name, step in learning_steps['preprocessing']:
    print(f"  • {name}: {type(step).__name__}")

print("\nTraining steps:")
for name, step in learning_steps['training']:
    print(f"  • {name}: {type(step).__name__}")
    
print("\n✓ Custom DBSCAN automatically calculates epsilon parameter")
print("✓ PCA reduces dimensionality while preserving variance")

# ============================================================================
# STEP 4: Complete Anomaly Detection Pipeline
# ============================================================================
print("\n\n4. ANOMALY DETECTION PIPELINE")
print("-" * 70)

from flight_ad.pipeline import AnomalyDetectionPipeline

# Combine all components into a single pipeline
ad_pipeline = AnomalyDetectionPipeline(binder, wrangler, learner)

print("Pipeline architecture:")
print("  1. DataBinder: Lazy-loads flight data from 400 flights")
print("  2. DataWrangler: Preprocesses and transforms each flight")
print("  3. StatisticalLearner: Applies ML pipeline for anomaly detection")

print("\nRunning anomaly detection on all flights...")
print("(This processes all 400 flights - may take a few minutes)")

# Fit the pipeline
ad_pipeline.fit()

print("✓ Pipeline training completed!")

# ============================================================================
# STEP 5: Results and Reporting
# ============================================================================
print("\n\n5. ANALYZING RESULTS")
print("-" * 70)

from flight_ad.report import clustering_info, silhouette

# Get clustering results
labels, n_clusters, n_noise = clustering_info(learner.pipeline['dbscan'])
avg_silhouette, sample_silhouette = silhouette(learner.partial_data['pca'], labels)

print(f"Clustering Results:")
print(f"  • Total flights processed: {len(labels)}")
print(f"  • Number of clusters found: {n_clusters}")
print(f"  • Anomalous flights (noise): {n_noise}")
print(f"  • Normal flights: {len(labels) - n_noise}")
print(f"  • Average silhouette score: {avg_silhouette:.4f}")
print(f"  • Anomaly rate: {n_noise/len(labels)*100:.2f}%")

# Show cluster distribution
print("\nCluster distribution:")
unique, counts = [], []
for label in sorted(set(labels)):
    count = list(labels).count(label)
    if label == -1:
        print(f"  • Anomalies (cluster -1): {count} flights")
    else:
        print(f"  • Cluster {label}: {count} flights")

# ============================================================================
# SUMMARY: How the Project Works
# ============================================================================
print("\n\n" + "=" * 70)
print("PROJECT WORKFLOW SUMMARY")
print("=" * 70)

summary = """
The flight-ad package implements an end-to-end anomaly detection pipeline 
for aviation data:

┌─────────────────────────────────────────────────────────────────┐
│ 1. DATA LOADING (DataBinder)                                    │
│    • Manages 400 NASA DASHlink flight recordings                │
│    • Lazy loading for memory efficiency                         │
│    • Flexible data binding with custom load functions           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. DATA WRANGLING (DataWrangler)                                │
│    • Extracts relevant flight phases (landing approach)         │
│    • Handles missing data imputation                            │
│    • Resamples to uniform time intervals                        │
│    • Selects key parameters (altitude, speed, etc.)             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. FEATURE ENGINEERING (StatisticalLearner - Preprocessing)     │
│    • Reshapes time series into feature vectors                  │
│    • Standardizes features (zero mean, unit variance)           │
│    • Applies PCA for dimensionality reduction                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. ANOMALY DETECTION (StatisticalLearner - Training)            │
│    • Custom DBSCAN clustering algorithm                         │
│    • Automatically calculates epsilon using curvature method    │
│    • Identifies normal patterns vs anomalies                    │
│    • Flights in small/no clusters = anomalies                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. REPORTING (Report Module)                                    │
│    • Cluster analysis and visualization                         │
│    • Silhouette scores for cluster quality                      │
│    • Anomaly identification and ranking                         │
└─────────────────────────────────────────────────────────────────┘

KEY INNOVATIONS:
• Adaptive DBSCAN: Automatically determines optimal epsilon parameter
  using curvature analysis instead of manual tuning
  
• Pipeline Architecture: Modular design allows easy customization of
  each stage (data loading, preprocessing, ML algorithms)
  
• Aviation-Specific: Tailored for flight data with time-series aware
  transformations and domain knowledge built-in
  
• Scalable: Handles large datasets efficiently with lazy loading and
  caching mechanisms
"""

print(summary)

print("\n" + "=" * 70)
print("DEMONSTRATION COMPLETE")
print("=" * 70)
