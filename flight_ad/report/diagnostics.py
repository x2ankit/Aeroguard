import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from flight_ad.pipeline.ad import bind_and_wrangle

__all__ = [
    'build_confidence_dashboard',
    'isolate_faults'
]


def _robust_stats(values: np.ndarray) -> Tuple[float, float]:
    median = np.median(values)
    mad = np.median(np.abs(values - median))
    if mad == 0:
        mad = np.std(values) if np.std(values) > 0 else 1e-6
    return median, mad


def _sensor_score(series: pd.Series, median: float, mad: float) -> float:
    values = pd.to_numeric(series, errors='coerce').dropna().values
    if values.size == 0:
        return np.nan
    z = np.abs((values - median) / mad)
    return float(np.median(z))


def build_confidence_dashboard(binder, wrangler, labels, flight_ids=None, anomaly_label=-1, top_n=3):
    """
    Build per-flight confidence scores and per-sensor contribution scores.
    Returns (dashboard_df, per_flight_sensor_scores).
    """
    wrangled = bind_and_wrangle(binder, wrangler)
    if flight_ids is None:
        flight_ids = list(binder.bindings.keys())

    # Determine numeric columns to score
    all_columns = []
    for df in wrangled:
        all_columns.extend(df.columns.tolist())
    all_columns = sorted(set(all_columns))
    numeric_columns = [c for c in all_columns if c != 'flight_id']

    normal_indices = [i for i, lbl in enumerate(labels) if lbl != anomaly_label]

    baseline_stats: Dict[str, Tuple[float, float]] = {}
    for col in numeric_columns:
        normal_values = []
        for i in normal_indices:
            series = pd.to_numeric(wrangled[i][col], errors='coerce').dropna()
            if not series.empty:
                normal_values.append(series.values)
        if normal_values:
            stacked = np.concatenate(normal_values)
            baseline_stats[col] = _robust_stats(stacked)

    per_flight_scores: List[Dict[str, float]] = []
    per_flight_confidence: List[float] = []
    top_sensors: List[List[Tuple[str, float]]] = []

    for i, df in enumerate(wrangled):
        scores = {}
        for col, (median, mad) in baseline_stats.items():
            scores[col] = _sensor_score(df[col], median, mad)

        # Convert to confidence in [0,1)
        confidences = {k: (1 - np.exp(-v)) if np.isfinite(v) else np.nan for k, v in scores.items()}
        conf_values = [v for v in confidences.values() if np.isfinite(v)]
        overall_conf = float(np.mean(conf_values)) if conf_values else np.nan

        sorted_sensors = sorted(
            [(k, confidences[k]) for k in confidences if np.isfinite(confidences[k])],
            key=lambda x: x[1],
            reverse=True
        )

        per_flight_scores.append(confidences)
        per_flight_confidence.append(overall_conf)
        top_sensors.append(sorted_sensors[:top_n])

    dashboard_rows = []
    for idx, flight_id in enumerate(flight_ids):
        row = {
            'flight_id': flight_id,
            'cluster_label': labels[idx],
            'is_anomaly': labels[idx] == anomaly_label,
            'overall_confidence': per_flight_confidence[idx]
        }
        for rank, (sensor, score) in enumerate(top_sensors[idx], start=1):
            row[f'top_sensor_{rank}'] = sensor
            row[f'top_sensor_{rank}_confidence'] = score
        for sensor, score in per_flight_scores[idx].items():
            row[f'conf_{sensor}'] = score
        dashboard_rows.append(row)

    dashboard_df = pd.DataFrame(dashboard_rows)
    return dashboard_df, per_flight_scores


def isolate_faults(sensor_confidence: Dict[str, float], top_n=3):
    """Return top-N sensors by confidence score."""
    ranked = sorted(
        [(k, v) for k, v in sensor_confidence.items() if np.isfinite(v)],
        key=lambda x: x[1],
        reverse=True
    )
    return ranked[:top_n]
