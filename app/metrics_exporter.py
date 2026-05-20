"""
app/metrics_exporter.py
------------------------
Reads metrics_data.json and exposes them as Prometheus metrics on port 8001.

Prometheus scrapes http://localhost:8001/metrics every 15 seconds.
The metrics update automatically when metrics_data.json changes.

Run:  python app/metrics_exporter.py
"""

import json
import os
import time
from prometheus_client import start_http_server, Gauge, REGISTRY, PROCESS_COLLECTOR, PLATFORM_COLLECTOR

# ── Remove default Python process metrics (keep output clean) ─────────────
# Comment these out if you want process/memory metrics too
REGISTRY.unregister(PROCESS_COLLECTOR)
REGISTRY.unregister(PLATFORM_COLLECTOR)

# ── Path to metrics data file ─────────────────────────────────────────────
DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "metrics_data.json")

# ── Define Prometheus Gauge metrics ──────────────────────────────────────
# Gauge = a value that can go up or down (perfect for recall, latency, etc.)
model_recall     = Gauge("model_recall",     "Model recall score",           ["demand_type"])
model_precision  = Gauge("model_precision",  "Model precision score",        ["demand_type"])
api_error_rate   = Gauge("api_error_rate",   "API error rate (0.0 to 1.0)")
api_latency_p95  = Gauge("api_latency_p95_ms", "API p95 latency in ms")
prediction_vol   = Gauge("prediction_volume","Prediction volume per hour",   ["demand_type"])


def load_and_update():
    """
    Read the latest values from metrics_data.json and update all Gauges.
    Called every 15 seconds so Prometheus always gets fresh values.
    """
    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)

        model_recall.labels(demand_type="BAT").set(data["model_recall_bat"])
        model_precision.labels(demand_type="BAT").set(data["model_precision_bat"])
        api_error_rate.set(data["api_error_rate"])
        api_latency_p95.set(data["api_latency_p95_ms"])
        prediction_vol.labels(demand_type="BAT").set(data["prediction_volume_bat"])

        print(f"[Exporter] Updated metrics — BAT recall={data['model_recall_bat']}")

    except FileNotFoundError:
        print(f"[Exporter] ERROR: {DATA_FILE} not found. Check the path.")
    except KeyError as e:
        print(f"[Exporter] ERROR: Missing key in metrics_data.json: {e}")
    except json.JSONDecodeError as e:
        print(f"[Exporter] ERROR: Invalid JSON in metrics_data.json: {e}")


if __name__ == "__main__":
    # Start HTTP server — Prometheus scrapes this
    start_http_server(8001)
    print("[Exporter] ✓ Metrics server running at http://localhost:8001/metrics")
    print("[Exporter]   Prometheus will scrape this every 15 seconds.")
    print("[Exporter]   BAT recall = 0.48 → alert will fire after ~15 seconds")
    print()

    # Update metrics in a loop
    while True:
        load_and_update()
        time.sleep(15)
