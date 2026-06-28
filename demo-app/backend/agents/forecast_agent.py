"""
Forecasts resource saturation trends (CPU, Storage, Network)
using linear regression over rolling window metrics.
"""

import asyncio
import os
import sys
import numpy as np
from datetime import datetime, timedelta
from sklearn.linear_model import LinearRegression

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database.db as db_mod
from models.forecast import DBForecast
from services.prometheus_service import PrometheusService

# Tunable constants
POLL_INTERVAL_SECONDS = 30         # How often the agent scrapes metrics
WINDOW_SIZE           = 20         # Number of samples kept per series
MIN_SAMPLES_REQUIRED  = 6          # Minimum samples before regression is meaningful
MAX_FORECAST_MINUTES  = 120        # Ignore predictions beyond 2 hours
DEDUP_WINDOW_MINUTES  = 3          # Suppress duplicate DB writes for the same forecast

# Saturation thresholds
CPU_THRESHOLD_CORES   = None       # Computed dynamically as 2.0× observed baseline
CPU_THRESHOLD_PCT     = 0.90       # Flag if CPU trend reaches 90 % of rolling max
STORAGE_THRESHOLD_PCT = 0.85       # 85 % PVC utilisation
NETWORK_LATENCY_MS    = 1000.0     # ms – high latency alert
NETWORK_DROP_PCT      = 5.0        # % packet-loss threshold

# In-memory history stores
_cpu_history     : dict[str, list[float]] = {}
_storage_history : dict[str, list[float]] = {}   # key = pvc_name
_network_history : dict[str, list[float]] = {}   # key = "src->tgt:metric"


def _fit_and_forecast(values: list[float], threshold: float, interval_seconds: int) -> dict:
    """Fits linear regression to predict minutes until threshold breach."""
    n = len(values)
    X = np.arange(n).reshape(-1, 1).astype(float)
    y = np.array(values, dtype=float)

    model = LinearRegression()
    model.fit(X, y)

    slope     = float(model.coef_[0])
    intercept = float(model.intercept_)

    # R² – model fit quality
    y_pred   = model.predict(X)
    ss_res   = np.sum((y - y_pred) ** 2)
    ss_tot   = np.sum((y - np.mean(y)) ** 2)
    r_squared = float(1 - ss_res / ss_tot) if ss_tot > 0 else 0.0

    current = values[-1]

    # If slope ≤ 0 the metric is stable or decreasing – no saturation risk
    minutes_to_breach = None
    predicted_at_horizon = current
    if slope > 1e-9:
        # intervals_until_breach = (threshold - current_value) / slope
        intervals = (threshold - current) / slope
        if 0 < intervals <= (MAX_FORECAST_MINUTES * 60 / interval_seconds):
            minutes_to_breach   = round(intervals * interval_seconds / 60.0, 1)
            predicted_at_horizon = round(current + slope * intervals, 4)

    return {
        "slope":               round(slope, 6),
        "r_squared":           round(r_squared, 4),
        "current":             round(current, 4),
        "predicted_at_horizon":predicted_at_horizon,
        "minutes_to_breach":   minutes_to_breach,
    }


def _severity(minutes: float | None) -> str:
    if minutes is None:
        return "Info"
    if minutes < 15:
        return "Critical"
    if minutes < 45:
        return "Warning"
    return "Info"


def _append_window(store: dict, key: str, value: float):
    if key not in store:
        store[key] = []
    store[key].append(value)
    if len(store[key]) > WINDOW_SIZE:
        store[key].pop(0)


async def _persist_forecast(
    db,
    resource_type: str,
    service_name: str,
    current_value: float,
    threshold: float,
    fc: dict,
    message: str,
    severity: str,
):
    """Write a DBForecast row, deduplicating within DEDUP_WINDOW_MINUTES."""
    dedup_limit = datetime.utcnow() - timedelta(minutes=DEDUP_WINDOW_MINUTES)
    existing = db.query(DBForecast).filter(
        DBForecast.resource_type == resource_type,
        DBForecast.service_name  == service_name,
        DBForecast.timestamp     >= dedup_limit,
    ).first()

    if existing:
        # Update in place
        existing.current_value     = current_value
        existing.predicted_value   = fc["predicted_at_horizon"]
        existing.minutes_to_breach = fc["minutes_to_breach"]
        existing.trend_slope       = fc["slope"]
        existing.r_squared         = fc["r_squared"]
        existing.message           = message
        existing.severity          = severity
        existing.timestamp         = datetime.utcnow()
        print(f"[ForecastAgent] Updated -> {service_name} {resource_type}: {message}")
    else:
        row = DBForecast(
            resource_type     = resource_type,
            service_name      = service_name,
            current_value     = current_value,
            predicted_value   = fc["predicted_at_horizon"],
            threshold         = threshold,
            minutes_to_breach = fc["minutes_to_breach"],
            trend_slope       = fc["slope"],
            r_squared         = fc["r_squared"],
            message           = message,
            severity          = severity,
        )
        db.add(row)
        print(f"[ForecastAgent] NEW FORECAST -> {service_name} {resource_type}: {message}")

    db.commit()


# CPU Forecasting

async def _run_cpu_forecast(prometheus: PrometheusService, db):
    try:
        metrics = await prometheus.get_cpu_metrics()
    except Exception as e:
        print(f"[ForecastAgent] CPU metrics fetch error: {e}")
        return

    for item in metrics:
        pod   = item["pod"]
        cores = item["cpu_cores"]

        if cores < 1e-5:
            continue  # skip idle / system pods

        _append_window(_cpu_history, pod, cores)
        history = _cpu_history[pod]

        if len(history) < MIN_SAMPLES_REQUIRED:
            continue

        # Dynamic threshold: 90 % of 3× the rolling maximum observed so far
        rolling_max = max(history)
        threshold   = rolling_max * 3.0 * CPU_THRESHOLD_PCT

        fc = _fit_and_forecast(history, threshold, POLL_INTERVAL_SECONDS)

        if fc["slope"] <= 1e-9:
            continue  # No upward trend – skip

        svc_label = pod.split("-")[0]  # "backend-abc123" → "backend"
        minutes   = fc["minutes_to_breach"]
        r2        = fc["r_squared"]

        if minutes is not None:
            msg = (
                f"CPU Saturation Forecast: {svc_label} CPU is trending upward "
                f"(slope: +{fc['slope']:.5f} cores/interval, R²={r2:.2f}). "
                f"Estimated to exceed threshold ({threshold:.4f} cores) in ≈{minutes} min."
            )
        else:
            msg = (
                f"CPU Trend Detected: {svc_label} CPU slope is +{fc['slope']:.5f} cores/interval "
                f"(R²={r2:.2f}). No saturation breach expected within {MAX_FORECAST_MINUTES} min."
            )

        sev = _severity(minutes)
        await _persist_forecast(
            db, "cpu", svc_label, fc["current"], threshold, fc, msg, sev
        )


# Storage Forecasting

async def _run_storage_forecast(prometheus: PrometheusService, db):
    try:
        pvcs = await prometheus.get_pvc_metrics()
    except Exception as e:
        print(f"[ForecastAgent] Storage metrics fetch error: {e}")
        return

    for pvc in pvcs:
        name = pvc["pvc_name"]
        pct  = pvc["percentage_used"]  # 0-100

        _append_window(_storage_history, name, pct)
        history = _storage_history[name]

        if len(history) < MIN_SAMPLES_REQUIRED:
            continue

        threshold = STORAGE_THRESHOLD_PCT * 100  # 85.0 %

        fc = _fit_and_forecast(history, threshold, POLL_INTERVAL_SECONDS)

        if fc["slope"] <= 1e-9:
            continue

        minutes = fc["minutes_to_breach"]
        r2      = fc["r_squared"]

        if minutes is not None:
            msg = (
                f"Storage Exhaustion Forecast: PVC '{name}' utilisation is growing "
                f"(slope: +{fc['slope']:.3f}%/interval, R²={r2:.2f}, currently {pct:.1f}%). "
                f"Estimated to exceed {int(threshold)}% capacity in ≈{minutes} min."
            )
        else:
            msg = (
                f"Storage Growth Trend: PVC '{name}' growing at +{fc['slope']:.3f}%/interval "
                f"(R²={r2:.2f}, currently {pct:.1f}%). "
                f"No saturation breach expected within {MAX_FORECAST_MINUTES} min."
            )

        sev = _severity(minutes)
        await _persist_forecast(
            db, "storage", name, pct, threshold, fc, msg, sev
        )


# Network Forecasting

async def _run_network_forecast(prometheus: PrometheusService, db):
    try:
        net_metrics = await prometheus.get_network_metrics()
    except Exception as e:
        print(f"[ForecastAgent] Network metrics fetch error: {e}")
        return

    for link in net_metrics:
        src = link["source_service"]
        tgt = link["target_service"]
        label = f"{src}->{tgt}"

        # Latency
        latency = link.get("latency_ms", 0.0)
        _append_window(_network_history, f"{label}:latency", latency)
        lat_history = _network_history[f"{label}:latency"]

        if len(lat_history) >= MIN_SAMPLES_REQUIRED:
            fc = _fit_and_forecast(lat_history, NETWORK_LATENCY_MS, POLL_INTERVAL_SECONDS)
            if fc["slope"] > 1e-9:
                minutes = fc["minutes_to_breach"]
                msg = (
                    f"Network Latency Forecast: {label} latency trending up "
                    f"(slope: +{fc['slope']:.2f} ms/interval, R²={fc['r_squared']:.2f}, current {latency:.1f} ms). "
                    + (
                        f"Estimated to exceed {int(NETWORK_LATENCY_MS)} ms in ≈{minutes} min."
                        if minutes else
                        f"No breach expected within {MAX_FORECAST_MINUTES} min."
                    )
                )
                sev = _severity(minutes)
                await _persist_forecast(
                    db, "network_latency", label, latency, NETWORK_LATENCY_MS, fc, msg, sev
                )

        # Packet Loss
        drop = link.get("packet_loss_rate", 0.0)
        _append_window(_network_history, f"{label}:drop", drop)
        drop_history = _network_history[f"{label}:drop"]

        if len(drop_history) >= MIN_SAMPLES_REQUIRED:
            fc = _fit_and_forecast(drop_history, NETWORK_DROP_PCT, POLL_INTERVAL_SECONDS)
            if fc["slope"] > 1e-9:
                minutes = fc["minutes_to_breach"]
                msg = (
                    f"Packet Loss Forecast: {label} packet-loss trending up "
                    f"(slope: +{fc['slope']:.4f}%/interval, R²={fc['r_squared']:.2f}, current {drop:.2f}%). "
                    + (
                        f"Estimated to exceed {NETWORK_DROP_PCT}% loss in ≈{minutes} min."
                        if minutes else
                        f"No breach expected within {MAX_FORECAST_MINUTES} min."
                    )
                )
                sev = _severity(minutes)
                await _persist_forecast(
                    db, "network_loss", label, drop, NETWORK_DROP_PCT, fc, msg, sev
                )


# Main agent loop

async def run_forecast_agent():
    print("[ForecastAgent] Predictive Saturation Forecast Agent started.")
    prometheus = PrometheusService()

    # Wait for DB and other agents to warm up
    await asyncio.sleep(15)

    while True:
        db = db_mod.SessionLocal()
        try:
            await _run_cpu_forecast(prometheus, db)
            await _run_storage_forecast(prometheus, db)
            await _run_network_forecast(prometheus, db)
        except Exception as e:
            print(f"[ForecastAgent] Unhandled error in forecast loop: {e}")
            db.rollback()
        finally:
            db.close()

        await asyncio.sleep(POLL_INTERVAL_SECONDS)
