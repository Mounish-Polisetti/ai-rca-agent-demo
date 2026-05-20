"""
app/report_generator.py
------------------------
Builds a structured prompt from all collected evidence and calls Gemini LLM
to generate a professional RCA report in Markdown format.

The prompt is carefully engineered to always produce the same 8 sections,
making the report consistent and easy to read every time.
"""

import os
import json
import google.generativeai as genai

MODEL_NAME = "gemini-2.0-flash-lite"   # current stable free-tier model (May 2026)


def generate_rca_report(evidence: dict, rag_context: str) -> str:
    """
    Generate a full RCA report using Gemini.

    Args:
        evidence:    The structured evidence dict from evidence_collector.
        rag_context: Similar past incidents retrieved by RAG.

    Returns:
        Markdown-formatted RCA report as a string.
    """
    api_key = os.environ.get("GEMINI_API_KEY", "")

    if not api_key:
        # Don't crash — return a placeholder report so the pipeline continues
        return _fallback_report(evidence)

    genai.configure(api_key=api_key)
    model  = genai.GenerativeModel(MODEL_NAME)
    prompt = _build_prompt(evidence, rag_context)

    print(f"[Gemini] Sending {len(prompt):,} char prompt to {MODEL_NAME}...")

    try:
        response = model.generate_content(prompt)
        report   = response.text
        print(f"[Gemini] ✓ Report received ({len(report):,} characters).")
        return report
    except Exception as e:
        print(f"[Gemini] ✗ API call failed: {e}")
        return _fallback_report(evidence, error=str(e))


def _build_prompt(evidence: dict, rag_context: str) -> str:
    """Construct the full prompt sent to Gemini."""

    metrics = evidence.get("metrics", {})
    drift   = evidence.get("drift",   {})
    grafana = evidence.get("grafana", {}).get("summary", {})
    alert   = evidence.get("alert_payload", {})

    # Format alert annotations nicely
    try:
        annotations = alert.get("alerts", [{}])[0].get("annotations", {})
    except (IndexError, AttributeError):
        annotations = {}

    return f"""
You are a senior MLOps Site Reliability Engineer performing a Root Cause Analysis.
An automated system detected a production model failure and collected evidence.
Analyze all evidence below and generate a complete, structured RCA report.

Be technical and specific. Use the exact metric values provided.
Do not invent data that is not in the evidence.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ALERT INFORMATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Alert Name   : {evidence.get('alert_name', 'BATRecallDrop')}
Demand Type  : {evidence.get('demand_type', 'BAT')}
Severity     : {evidence.get('severity', 'warning').upper()}
Triggered At : {evidence.get('collected_at', 'Unknown')}
Summary      : {annotations.get('summary', 'BAT recall dropped below threshold')}
Description  : {annotations.get('description', 'BAT model recall is below 0.55')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PROMETHEUS METRICS EVIDENCE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
model_recall (BAT)      : {metrics.get('model_recall_bat', 'N/A')}   ← BELOW threshold 0.55
model_precision (BAT)   : {metrics.get('model_precision_bat', 'N/A')}
api_error_rate          : {metrics.get('api_error_rate', 'N/A')}
api_latency_p95_ms      : {metrics.get('api_latency_p95_ms', 'N/A')}
prediction_volume (BAT) : {metrics.get('prediction_volume_bat', 'N/A')}
model_version           : {metrics.get('model_version', 'N/A')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURE DRIFT EVIDENCE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
battery_status_null_rate:
  - Previous (normal) : {drift.get('battery_status_null_rate', {}).get('previous', 'N/A')}
  - Current (now)     : {drift.get('battery_status_null_rate', {}).get('current', 'N/A')}  ← CRITICAL SPIKE

vehicle_age_mean:
  - Training baseline : {drift.get('vehicle_age_mean', {}).get('training', 'N/A')}
  - Current           : {drift.get('vehicle_age_mean', {}).get('current', 'N/A')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GRAFANA DASHBOARD SNAPSHOT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Dashboard       : {evidence.get('grafana', {}).get('dashboard', 'N/A')}
BAT Recall Trend: {grafana.get('BAT_recall_trend', 'N/A')}
API Health      : {grafana.get('API_health', 'N/A')}
Model Version   : {grafana.get('model_version', 'N/A')}
Key Observation : {grafana.get('main_observation', 'N/A')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HISTORICAL CONTEXT — SIMILAR PAST INCIDENTS (from RAG/FAISS)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{rag_context}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INSTRUCTIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Generate a professional RCA report in Markdown format with EXACTLY these sections:

# AI Root Cause Analysis Report — BAT Recall Drop

## 1. Alert Summary
What alert fired, when, what metric value, what threshold was breached.

## 2. Likely Root Cause
The most probable technical reason based on all evidence. Be specific.
Reference actual PSI/null-rate values. State your reasoning clearly.

## 3. Supporting Evidence
Bullet list of every data point that supports the root cause.
Include metric values, drift numbers, Grafana observations.

## 4. Historical Incident Comparison
How does this compare to similar past incidents retrieved from the knowledge base?
Did we see this pattern before? What resolved it then?

## 5. Recommended Action
Step-by-step numbered list:
- IMMEDIATE (within 1 hour)
- SHORT-TERM (within 24 hours)
- MEDIUM-TERM (within 1 week)

## 6. Retrain / Wait / Fix Pipeline Decision
Make one of these three decisions and justify it clearly:
- RETRAIN MODEL: if drift is severe and irreversible
- FIX PIPELINE: if the issue is in data feed or feature engineering
- WAIT AND MONITOR: if the issue is transient

## 7. Confidence Level
Rate: HIGH / MEDIUM / LOW
Explain your confidence based on evidence quality.
State any gaps or uncertainties.

## 8. Prevention Recommendations
What monitoring rules, data quality checks, or process changes would
prevent this class of incident from recurring?
""".strip()


def _fallback_report(evidence: dict, error: str = "") -> str:
    """Return a minimal report when Gemini is not available."""
    metrics     = evidence.get("metrics", {})
    error_note  = f"\n\n**API Error:** {error}" if error else ""
    return f"""# AI Root Cause Analysis Report — BAT Recall Drop

> ⚠️ This is a fallback report. GEMINI_API_KEY is not set or the API call failed.{error_note}

## 1. Alert Summary
Alert: {evidence.get('alert_name', 'BATRecallDrop')}
BAT model recall = **{metrics.get('model_recall_bat', 'N/A')}** (threshold: 0.55)
Triggered at: {evidence.get('collected_at', 'N/A')}

## 2. Likely Root Cause
Unable to generate AI analysis. Set GEMINI_API_KEY in .env to enable.

## 3. Raw Evidence
- model_recall_bat      : {metrics.get('model_recall_bat')}
- battery_status_null   : {evidence.get('drift', {}).get('battery_status_null_rate', {}).get('current', 'N/A')}
- model_version         : {metrics.get('model_version')}

## Next Step
Add your Gemini API key to .env and re-run the pipeline.
Get a free key at: https://aistudio.google.com/app/apikey
"""
