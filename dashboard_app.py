import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from pathlib import Path
from sklearn.decomposition import PCA
import numpy as np

DATA_DIR = Path(__file__).parent
DASHBOARD_FILE = DATA_DIR / "fault_isolation_dashboard.csv"
ANOMALY_FILE = DATA_DIR / "anomalies_only.csv"
REPORT_FILE = DATA_DIR / "anomaly_report.csv"

st.set_page_config(page_title="Flight Fault Awareness Dashboard", layout="wide")

st.title("Flight Fault Awareness & Prognostics")
st.caption("Advanced anomaly detection with per-sensor fault isolation and confidence scoring")


@st.cache_data
def load_data():
    if not DASHBOARD_FILE.exists():
        return None, None, None
    dashboard_df = pd.read_csv(DASHBOARD_FILE)
    anomalies_df = pd.read_csv(ANOMALY_FILE) if ANOMALY_FILE.exists() else None
    report_df = pd.read_csv(REPORT_FILE) if REPORT_FILE.exists() else None
    return dashboard_df, anomalies_df, report_df


dashboard_df, anomalies_df, report_df = load_data()

if dashboard_df is None:
    st.error("fault_isolation_dashboard.csv not found. Run anomaly_storage_guide.py first.")
    st.stop()


# Sidebar filters
with st.sidebar:
    st.header("Filters")
    show_anomalies_only = st.checkbox("Show anomalies only", value=True)
    top_n = st.slider("Top sensors to display", min_value=1, max_value=5, value=3)

filtered_df = dashboard_df.copy()
if show_anomalies_only:
    filtered_df = filtered_df[filtered_df["is_anomaly"] == True]

# KPIs
col1, col2, col3, col4 = st.columns(4)

anomaly_count = int(dashboard_df["is_anomaly"].sum())
flight_count = int(len(dashboard_df))
anomaly_rate = (anomaly_count / flight_count) * 100 if flight_count else 0
avg_conf = dashboard_df["overall_confidence"].mean()

col1.metric("Flights Analyzed", f"{flight_count:,}")
col2.metric("Anomalies Detected", f"{anomaly_count:,}")
col3.metric("Anomaly Rate", f"{anomaly_rate:.2f}%")
col4.metric("Avg Confidence", f"{avg_conf:.3f}")

st.divider()

# Anomaly Clustering Visualization
st.subheader("Anomaly Clustering & Detection Boundaries")
if dashboard_df is not None and len(dashboard_df[dashboard_df["is_anomaly"] == True]) > 0:
    try:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Cluster Distribution**")
            if "cluster_label" in dashboard_df.columns:
                cluster_counts = dashboard_df["cluster_label"].value_counts()
                fig_cluster = px.pie(
                    values=cluster_counts.values,
                    names=[f"Cluster {int(c)}" if c >= 0 else "Anomalies" for c in cluster_counts.index],
                    color_discrete_sequence=['#1f77b4', '#d62728', '#ff7f0e', '#2ca02c', '#9467bd']
                )
                st.plotly_chart(fig_cluster, use_container_width=True)
        
        with col2:
            st.markdown("**Anomaly Severity Distribution**")
            severity_data = pd.DataFrame({
                'Severity': ['HIGH', 'MEDIUM', 'LOW'],
                'Count': [
                    len(dashboard_df[(dashboard_df['is_anomaly']) & (dashboard_df['overall_confidence'] >= 0.8)]),
                    len(dashboard_df[(dashboard_df['is_anomaly']) & (dashboard_df['overall_confidence'] >= 0.5) & (dashboard_df['overall_confidence'] < 0.8)]),
                    len(dashboard_df[(dashboard_df['is_anomaly']) & (dashboard_df['overall_confidence'] < 0.5)])
                ]
            })
            fig_sev = px.bar(
                severity_data,
                x='Severity',
                y='Count',
                color='Severity',
                color_discrete_map={'HIGH': '#d62728', 'MEDIUM': '#ff7f0e', 'LOW': '#1f77b4'}
            )
            st.plotly_chart(fig_sev, use_container_width=True)
    except Exception as e:
        st.warning(f"Could not render clustering visualization: {e}")

st.divider()

# Anomaly table
st.subheader("Anomaly List with Top Sensor Contributors")

columns = [
    "flight_id",
    "cluster_label",
    "overall_confidence",
] + [f"top_sensor_{i}" for i in range(1, top_n + 1)] + [f"top_sensor_{i}_confidence" for i in range(1, top_n + 1)]

columns = [c for c in columns if c in filtered_df.columns]

st.dataframe(
    filtered_df[columns].sort_values("overall_confidence", ascending=False),
    use_container_width=True
)

st.divider()

# Confidence distribution
st.subheader("Confidence Distribution")
fig_conf = px.histogram(
    dashboard_df,
    x="overall_confidence",
    color="is_anomaly",
    nbins=30,
    color_discrete_map={True: "#d62728", False: "#1f77b4"},
    labels={"is_anomaly": "Anomaly"}
)
fig_conf.update_layout(legend_title_text="")
st.plotly_chart(fig_conf, use_container_width=True)

st.divider()

# Sensor heatmap (anomalies only)
st.subheader("Per-Sensor Confidence Heatmap (Anomalies)")
conf_cols = [c for c in dashboard_df.columns if c.startswith("conf_")]
if conf_cols:
    heat_df = dashboard_df[dashboard_df["is_anomaly"] == True][conf_cols]
    heat_df.index = dashboard_df[dashboard_df["is_anomaly"] == True]["flight_id"]
    fig_heat = px.imshow(
        heat_df,
        aspect="auto",
        color_continuous_scale="RdYlBu_r",
        labels={"x": "Sensor", "y": "Flight ID", "color": "Confidence"}
    )
    st.plotly_chart(fig_heat, use_container_width=True)
else:
    st.info("No per-sensor confidence columns found.")

st.divider()

# Sensor impact summary
st.subheader("Top Sensor Contributors (Aggregate)")
if conf_cols:
    mean_conf = dashboard_df[conf_cols].mean().sort_values(ascending=False)
    top_sensors = mean_conf.head(10).reset_index()
    top_sensors.columns = ["sensor", "mean_confidence"]
    top_sensors["sensor"] = top_sensors["sensor"].str.replace("conf_", "", regex=False)

    fig_bar = px.bar(
        top_sensors,
        x="sensor",
        y="mean_confidence",
        color="mean_confidence",
        color_continuous_scale="Blues"
    )
    st.plotly_chart(fig_bar, use_container_width=True)

st.divider()

# 3D PCA Visualization
st.subheader("3D Anomaly Space (PCA Projection)")
if dashboard_df is not None:
    try:
        from sklearn.decomposition import PCA
        import numpy as np
        
        # Extract per-sensor confidence columns
        conf_cols = [c for c in dashboard_df.columns if c.startswith("conf_")]
        if conf_cols:
            X = dashboard_df[conf_cols].values
            
            # Fit PCA to 3D
            pca_3d = PCA(n_components=3)
            X_pca_3d = pca_3d.fit_transform(X)
            
            # Create 3D scatter
            import plotly.graph_objects as go
            
            normal_mask = dashboard_df["is_anomaly"] == False
            anomaly_mask = dashboard_df["is_anomaly"] == True
            
            fig_3d = go.Figure()
            
            # Normal flights
            fig_3d.add_trace(go.Scatter3d(
                x=X_pca_3d[normal_mask, 0],
                y=X_pca_3d[normal_mask, 1],
                z=X_pca_3d[normal_mask, 2],
                mode='markers',
                marker=dict(size=5, color='#1f77b4', opacity=0.6),
                text=dashboard_df[normal_mask]["flight_id"],
                hovertemplate="<b>%{text}</b><br>PC1: %{x:.2f}<br>PC2: %{y:.2f}<br>PC3: %{z:.2f}<extra></extra>",
                name="Normal"
            ))
            
            # Anomalous flights
            fig_3d.add_trace(go.Scatter3d(
                x=X_pca_3d[anomaly_mask, 0],
                y=X_pca_3d[anomaly_mask, 1],
                z=X_pca_3d[anomaly_mask, 2],
                mode='markers',
                marker=dict(size=8, color='#d62728', opacity=0.9, symbol='diamond'),
                text=dashboard_df[anomaly_mask]["flight_id"],
                hovertemplate="<b>%{text}</b><br>PC1: %{x:.2f}<br>PC2: %{y:.2f}<br>PC3: %{z:.2f}<extra></extra>",
                name="Anomaly"
            ))
            
            fig_3d.update_layout(
                title="3D PCA Projection: Normal vs Anomalous Flights",
                scene=dict(
                    xaxis_title="Principal Component 1",
                    yaxis_title="Principal Component 2",
                    zaxis_title="Principal Component 3"
                ),
                height=700,
                showlegend=True
            )
            
            st.plotly_chart(fig_3d, use_container_width=True)
        else:
            st.info("No per-sensor confidence columns for 3D visualization.")
    except Exception as e:
        st.error(f"Error creating 3D visualization: {e}")

st.divider()

# 2D PCA Visualization
st.subheader("2D Anomaly Space (PCA Projection)")
if dashboard_df is not None:
    try:
        conf_cols = [c for c in dashboard_df.columns if c.startswith("conf_")]
        if conf_cols:
            X = dashboard_df[conf_cols].values
            pca_2d = PCA(n_components=2)
            X_pca_2d = pca_2d.fit_transform(X)
            
            df_pca = pd.DataFrame({
                'PC1': X_pca_2d[:, 0],
                'PC2': X_pca_2d[:, 1],
                'flight_id': dashboard_df['flight_id'],
                'is_anomaly': dashboard_df['is_anomaly'],
                'confidence': dashboard_df['overall_confidence']
            })
            
            fig_2d = px.scatter(
                df_pca,
                x='PC1',
                y='PC2',
                color='is_anomaly',
                size='confidence',
                hover_data=['flight_id', 'confidence'],
                color_discrete_map={True: '#d62728', False: '#1f77b4'},
                labels={'is_anomaly': 'Anomaly'},
                title='2D PCA Projection: Anomaly Detection Space'
            )
            st.plotly_chart(fig_2d, use_container_width=True)
    except Exception as e:
        st.error(f"Error creating 2D visualization: {e}")

st.divider()

# Sensor Parameter Space Visualization
st.subheader("3D Sensor Parameter Space (RALT vs CAS vs ALT)")
if dashboard_df is not None:
    try:
        # Check if we have sensor confidence columns
        conf_cols = [c for c in dashboard_df.columns if c.startswith("conf_")]
        sensor_map = {
            'conf_RALT': 'RALT',
            'conf_CAS': 'CAS',
            'conf_ALT': 'ALT',
            'conf_WOW': 'WOW'
        }
        
        available_sensors = [sensor_map[c] for c in conf_cols if c in sensor_map]
        
        if len(available_sensors) >= 3:
            # Use top 3 sensors for visualization
            sensors_to_plot = available_sensors[:3]
            col_names = [f"conf_{s}" for s in sensors_to_plot]
            
            # Create 3D scatter of sensor confidence space
            fig_sensor_3d = go.Figure()
            
            normal_mask = dashboard_df["is_anomaly"] == False
            anomaly_mask = dashboard_df["is_anomaly"] == True
            
            # Normal flights
            fig_sensor_3d.add_trace(go.Scatter3d(
                x=dashboard_df[normal_mask][col_names[0]],
                y=dashboard_df[normal_mask][col_names[1]],
                z=dashboard_df[normal_mask][col_names[2]],
                mode='markers',
                marker=dict(size=4, color='#1f77b4', opacity=0.5),
                text=dashboard_df[normal_mask]["flight_id"],
                hovertemplate="<b>%{text}</b><br>" + sensors_to_plot[0] + ": %{x:.3f}<br>" + sensors_to_plot[1] + ": %{y:.3f}<br>" + sensors_to_plot[2] + ": %{z:.3f}<extra></extra>",
                name="Normal"
            ))
            
            # Anomalous flights
            fig_sensor_3d.add_trace(go.Scatter3d(
                x=dashboard_df[anomaly_mask][col_names[0]],
                y=dashboard_df[anomaly_mask][col_names[1]],
                z=dashboard_df[anomaly_mask][col_names[2]],
                mode='markers',
                marker=dict(size=10, color='#d62728', opacity=0.95, symbol='diamond'),
                text=dashboard_df[anomaly_mask]["flight_id"],
                hovertemplate="<b>%{text}</b><br>" + sensors_to_plot[0] + ": %{x:.3f}<br>" + sensors_to_plot[1] + ": %{y:.3f}<br>" + sensors_to_plot[2] + ": %{z:.3f}<extra></extra>",
                name="Anomaly"
            ))
            
            fig_sensor_3d.update_layout(
                title=f"Sensor Confidence Space: {sensors_to_plot[0]} × {sensors_to_plot[1]} × {sensors_to_plot[2]}",
                scene=dict(
                    xaxis_title=f"{sensors_to_plot[0]} Confidence",
                    yaxis_title=f"{sensors_to_plot[1]} Confidence",
                    zaxis_title=f"{sensors_to_plot[2]} Confidence",
                    xaxis=dict(range=[0, 1]),
                    yaxis=dict(range=[0, 1]),
                    zaxis=dict(range=[0, 1])
                ),
                height=700,
                showlegend=True
            )
            
            st.plotly_chart(fig_sensor_3d, use_container_width=True)
        else:
            st.info("Insufficient sensor data for 3D parameter space visualization.")
    except Exception as e:
        st.error(f"Error creating sensor parameter space: {e}")

st.divider()

# Advanced Sensor Correlation Matrix
st.subheader("Sensor Correlation in Anomalies (What Fails Together)")
if dashboard_df is not None:
    try:
        conf_cols = [c for c in dashboard_df.columns if c.startswith("conf_")]
        if len(conf_cols) >= 2:
            # Compute correlation matrix for anomalies
            anomaly_subset = dashboard_df[dashboard_df["is_anomaly"] == True][conf_cols]
            if len(anomaly_subset) > 1:
                corr_matrix = anomaly_subset.corr()
                
                # Rename columns for display
                sensor_names = [c.replace("conf_", "") for c in conf_cols]
                corr_matrix.index = sensor_names
                corr_matrix.columns = sensor_names
                
                fig_corr = go.Figure(data=go.Heatmap(
                    z=corr_matrix.values,
                    x=sensor_names,
                    y=sensor_names,
                    colorscale='RdBu',
                    zmid=0,
                    text=np.round(corr_matrix.values, 2),
                    texttemplate='%{text:.2f}',
                    textfont={"size": 12},
                    hovertemplate="%{x} ↔ %{y}: %{z:.3f}<extra></extra>"
                ))
                
                fig_corr.update_layout(
                    title="Sensor Anomaly Correlation: Which Sensors Fail Together?",
                    height=400
                )
                
                st.plotly_chart(fig_corr, use_container_width=True)
                
                st.markdown("""
                **Interpretation:**
                - **Red cells** (positive correlation): Sensors fail together (linked failure modes)
                - **Blue cells** (negative correlation): When one sensor deviant, others are normal
                - **White cells** (no correlation): Independent sensor failures
                
                **Example:** High ALT-CAS correlation → Likely pressure system issue affecting both altitude & airspeed
                """)
    except Exception as e:
        st.warning(f"Could not compute sensor correlation: {e}")

st.divider()

# Report quick view
st.subheader("Report Snapshot")
if report_df is not None:
    st.dataframe(report_df.head(20), use_container_width=True)
else:
    st.info("anomaly_report.csv not found.")
