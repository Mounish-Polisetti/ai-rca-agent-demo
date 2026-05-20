"""
app/evidence_collector.py
--------------------------
Reads all mock evidence files and combines them with the alert payload
into a single structured dictionary for the RCA pipeline.

In production this would call:
  - Prometheus HTTP API for metric history
  - Grafana API for real dashboard snapshots
  - Feature store for drift scores
  - Data pipeline logs for freshness

Here we read pre-written JSON files that simulate those responses.
"""

import json
import os
from datetime import datetime, timezone

# ── Paths to mock evidence files ──────────────────────────────────────────
BASE_DIR      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR      = os.path.join(BASE_DIR, "data")
METRICS_FILE  = os.path.join(DATA_DIR, "metrics_data.json")
DRIFT_FILE    = os.path.join(DATA_DIR, "drift_report.json")
GRAFANA_FILE  = os.path.join(DATA_DIR, "grafana_snapshot.json")


def collect_evidence(alert_payload: dict) -> dict:
    """
    Collect all evidence for the RCA workflow.

    Args:
        alert_payload: The raw JSON payload received from Alertmanager.

    Returns:
        A structured dictionary containing all evidence.
    """
    print("[Evidence] Collecting evidence files...")

    evidence = {
        "collected_at":    datetime.now(timezone.utc).isoformat(),
        "alert_payload":   alert_payload,
        "alert_name":      _extract_alert_name(alert_payload),
        "demand_type":     _extract_label(alert_payload, "demand_type", "BAT"),
        "severity":        _extract_label(alert_payload, "severity", "warning"),
        "metrics":         _read_json(METRICS_FILE,  "metrics_data"),
        "drift":           _read_json(DRIFT_FILE,    "drift_report"),
        "grafana":         _read_json(GRAFANA_FILE,  "grafana_snapshot"),
    }

    print(f"[Evidence] ✓ Alert:   {evidence['alert_name']}")
    print(f"[Evidence] ✓ Metrics: recall={evidence['metrics'].get('model_recall_bat', 'N/A')}")
    print(f"[Evidence] ✓ Drift:   battery_status_null_rate current="
          f"{evidence['drift'].get('battery_status_null_rate', {}).get('current', 'N/A')}")
    return evidence


def _read_json(filepath: str, label: str) -> dict:
    """Read a JSON file and return its contents. Return empty dict on error."""
    try:
        with open(filepath, "r") as f:
            data = json.load(f)
        print(f"[Evidence] ✓ Loaded {label} from {os.path.basename(filepath)}")
        return data
    except FileNotFoundError:
        print(f"[Evidence] ✗ File not found: {filepath}")
        return {"error": f"{label} file not found"}
    except json.JSONDecodeError as e:
        print(f"[Evidence] ✗ Invalid JSON in {filepath}: {e}")
        return {"error": f"Invalid JSON: {e}"}


def _extract_alert_name(payload: dict) -> str:
    try:
        return (payload.get("alerts", [{}])[0]
                       .get("labels", {})
                       .get("alertname", "UnknownAlert"))
    except (IndexError, AttributeError):
        return "UnknownAlert"


def _extract_label(payload: dict, key: str, default: str) -> str:
    try:
        return (payload.get("alerts", [{}])[0]
                       .get("labels", {})
                       .get(key, default))
    except (IndexError, AttributeError):
        return default
