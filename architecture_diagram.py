"""
Architecture Visualization Script
Creates a visual representation of the flight-ad pipeline
"""

def print_architecture():
    print("""
╔══════════════════════════════════════════════════════════════════════════╗
║                    FLIGHT-AD ARCHITECTURE OVERVIEW                        ║
╚══════════════════════════════════════════════════════════════════════════╝

┌──────────────────────────────────────────────────────────────────────────┐
│                         1. DATA SOURCE LAYER                              │
├──────────────────────────────────────────────────────────────────────────┤
│  NASA DASHlink Dataset                                                    │
│  ├─ 400 flight recordings                                                 │
│  ├─ ~850 MB compressed (parquet format)                                  │
│  └─ Parameters: RALT, CAS, ALT, WOW, etc. (191 total)                   │
│                                                                            │
│  Component: dashlink.py                                                   │
│  Functions: load_dashlink_bindings(), download_dataset()                 │
└──────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌──────────────────────────────────────────────────────────────────────────┐
│                      2. DATA BINDING LAYER                                │
├──────────────────────────────────────────────────────────────────────────┤
│  DataBinder                                                               │
│  ├─ Lazy loading: data loaded on-demand                                  │
│  ├─ Iterator interface: for flight in binder.iterdata()                  │
│  ├─ Custom bind functions: flexible data loading                         │
│  └─ Memory efficient: doesn't load all at once                           │
│                                                                            │
│  Component: utils/data/interface.py                                       │
│  Key Methods: retrieve_data(), iterdata(), apply_to_all()                │
└──────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌──────────────────────────────────────────────────────────────────────────┐
│                    3. DATA WRANGLING LAYER                                │
├──────────────────────────────────────────────────────────────────────────┤
│  DataWrangler (Function Pipeline)                                        │
│                                                                            │
│  Step 1: preprocess_flight                                               │
│  │  ├─ Use full flight timeline                                          │
│  │  └─ Map categorical → numeric (WOW: GROUND→0, AIR→1)                 │
│  │                                                                         │
│  Step 2: resample_dataframe                                              │
│  │  ├─ Interpolate to uniform intervals                                  │
│  │  └─ Normalize to 282 samples                                          │
│  │                                                                         │
│  Step 3: change_col                                                       │
│  │  └─ Re-reference time to start of flight (t=0)                        │
│  │                                                                         │
│  Step 4: select_col                                                       │
│  │  └─ Select key parameters (RALT, etc.)                                │
│  │                                                                         │
│  Result: 105,152 × 191 → 282 × 1                                         │
│                                                                            │
│  Component: wrangling/wrangler.py                                         │
│  Key Methods: compose(), named_steps                                     │
└──────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌──────────────────────────────────────────────────────────────────────────┐
│                  4. FEATURE ENGINEERING LAYER                             │
├──────────────────────────────────────────────────────────────────────────┤
│  StatisticalLearner - Preprocessing Pipeline                             │
│                                                                            │
│  Stage 1: reshape_df_interspersed                                        │
│  │  └─ Time series → feature vector                                      │
│  │     [x₁_t₁, x₂_t₁, ..., xₙ_t₁, x₁_t₂, ...]                          │
│  │                                                                         │
│  Stage 2: StandardScaler                                                 │
│  │  ├─ Mean = 0                                                           │
│  │  └─ Std Dev = 1                                                        │
│  │                                                                         │
│  Stage 3: PCA (Principal Component Analysis)                             │
│  │  ├─ Input: 282 dimensions                                             │
│  │  ├─ Output: 10 principal components                                   │
│  │  └─ Preserves ~90% of variance                                        │
│  │                                                                         │
│  Component: learn/stats_learner.py                                        │
│  Key Feature: Records intermediate outputs (record='pca')                │
└──────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌──────────────────────────────────────────────────────────────────────────┐
│                   5. ANOMALY DETECTION LAYER                              │
├──────────────────────────────────────────────────────────────────────────┤
│  Custom DBSCAN Clustering                                                │
│                                                                            │
│  Innovation: Automatic Epsilon Calculation                               │
│  │                                                                         │
│  │  Step 1: Compute k-nearest neighbors (k=2)                            │
│  │  Step 2: Sort distances                                               │
│  │  Step 3: Calculate curvature of distance plot                         │
│  │  Step 4: Select epsilon at max curvature                              │
│  │                                                                         │
│  │  Mathematics:                                                          │
│  │  κ(x) = |f''(x)| / (1 + f'(x)²)^(3/2)                                │
│  │  ε = y[argmax(κ(x))]                                                  │
│  │                                                                         │
│  Algorithm:                                                               │
│  ├─ Dense regions → clusters (normal flights)                            │
│  ├─ Sparse regions → noise (anomalies)                                   │
│  └─ Parameters: min_samples=5, auto epsilon                              │
│                                                                            │
│  Component: cluster/_dbscan.py                                            │
│  Key Methods: calculate_eps(), fit(), fit_predict()                      │
└──────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌──────────────────────────────────────────────────────────────────────────┐
│                      6. REPORTING LAYER                                   │
├──────────────────────────────────────────────────────────────────────────┤
│  Clustering Analysis                                                      │
│                                                                            │
│  Metrics:                                                                 │
│  ├─ Cluster count: Number of flight patterns                             │
│  ├─ Noise count: Number of anomalies                                     │
│  ├─ Silhouette score: Cluster quality (-1 to 1)                          │
│  └─ Sample scores: Per-flight anomaly measure                            │
│                                                                            │
│  Output Example:                                                          │
│  ├─ Total flights: 400                                                   │
│  ├─ Clusters: 1                                                           │
│  ├─ Normal flights: 383 (95.75%)                                         │
│  ├─ Anomalies: 17 (4.25%)                                                │
│  └─ Silhouette: 0.4153                                                   │
│                                                                            │
│  Component: report/cluster.py                                             │
│  Key Functions: clustering_info(), silhouette()                          │
└──────────────────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════
                         PIPELINE ORCHESTRATION
═══════════════════════════════════════════════════════════════════════════

AnomalyDetectionPipeline (pipeline/ad.py)
│
├─ fit()
│  ├─ For each flight in binder:
│  │  ├─ Wrangle data (DataWrangler)
│  │  └─ Collect processed flights
│  │
│  └─ Apply ML pipeline (StatisticalLearner)
│     ├─ Preprocessing (reshape, scale, PCA)
│     └─ Training (DBSCAN clustering)
│
├─ fit_predict()
│  └─ Same as fit() but returns cluster labels
│
└─ predict(new_data)
   └─ Apply trained pipeline to new flights

═══════════════════════════════════════════════════════════════════════════
                            DATA FLOW DIAGRAM
═══════════════════════════════════════════════════════════════════════════

Input                    Processing                         Output
─────                    ──────────                         ──────

Flight File          ┌─→ Load (parquet)
(~2 MB each)         │   105k samples                    
                     │   191 parameters          
                     │                                   
                     ├─→ Wrangle                        Clean Time
                     │   • Full flight                  Series
                     │   • Resample                     282 × 1
                     │   • Normalize                    
                     │                                   
                     ├─→ Feature Eng.                   Feature
                     │   • Reshape                      Vector
                     │   • Scale                        282 dims
                     │   • PCA reduce                   → 10 dims
                     │                                   
                     └─→ Cluster                        Label
                         • DBSCAN                       0 or -1
                         • Auto epsilon                 (normal/
                                                        anomaly)

═══════════════════════════════════════════════════════════════════════════
                          KEY DESIGN PATTERNS
═══════════════════════════════════════════════════════════════════════════

1. ADAPTER PATTERN
   └─ DataBinder adapts various data sources to uniform interface

2. PIPELINE PATTERN
   └─ Sequential transformations with intermediate caching

3. STRATEGY PATTERN
   └─ Swappable wrangling/learning steps

4. LAZY EVALUATION
   └─ LRU cache prevents redundant computation

5. ITERATOR PATTERN
   └─ Memory-efficient processing of large datasets

6. TEMPLATE METHOD
   └─ StatisticalLearner extends sklearn.pipeline.Pipeline

═══════════════════════════════════════════════════════════════════════════
""")

if __name__ == "__main__":
    print_architecture()
