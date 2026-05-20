"""
app/rca_service.py
-------------------
FastAPI application — the main RCA orchestration service.

Endpoint: POST /trigger-rca
  Receives the Alertmanager webhook payload, runs the full RCA pipeline,
  saves the report, and sends an email.

Also provides: GET /health  (for checking the service is up)

Run:
  uvicorn app.rca_service:app --host 0.0.0.0 --port 8000 --reload

Alertmanager sends to: http://host.docker.internal:8000/trigger-rca
"""

import os
import sys
from datetime import datetime, timezone

from fastapi          import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

# ── Load .env before anything else ───────────────────────────────────────
# This ensures GEMINI_API_KEY and email vars are available to all modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.utils import load_dotenv_manual
load_dotenv_manual()

from app.evidence_collector import collect_evidence
from app.rag_retriever      import retrieve_similar_incidents
from app.report_generator   import generate_rca_report
from app.email_sender       import send_email
from app.utils              import save_report, pretty_json

# ── Output directory ──────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")

# ── FastAPI app ───────────────────────────────────────────────────────────
app = FastAPI(
    title="AI RCA Agent",
    description="Automated Root Cause Analysis triggered by Alertmanager webhook",
    version="1.0.0",
)


@app.get("/health")
def health_check():
    """Simple health check — confirms the service is running."""
    return {
        "status":    "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service":   "ai-rca-agent",
    }


@app.post("/trigger-rca")
async def trigger_rca(request: Request):
    """
    Main RCA endpoint — called by Alertmanager when an alert fires.

    Alertmanager sends a JSON body like:
    {
      "version": "4",
      "status":  "firing",
      "alerts":  [{ "labels": {...}, "annotations": {...}, ... }]
    }

    Returns JSON with: status, report_path, email_status
    """
    print("\n" + "=" * 60)
    print("[RCA Service] ← Webhook received from Alertmanager")
    print(f"[RCA Service]   Time: {datetime.now(timezone.utc).isoformat()}")

    # ── Parse incoming JSON ───────────────────────────────────────────────
    try:
        payload = await request.json()
    except Exception as e:
        print(f"[RCA Service] ✗ Failed to parse JSON payload: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

    print(f"[RCA Service]   Alert status: {payload.get('status', 'unknown')}")
    print(f"[RCA Service]   Alerts count: {len(payload.get('alerts', []))}")

    # ── Only process firing alerts (skip resolved) ────────────────────────
    if payload.get("status") == "resolved":
        print("[RCA Service] Alert is resolved — skipping RCA.")
        return JSONResponse({"status": "skipped", "reason": "alert resolved"})

    # ── Extract alert name for logging ────────────────────────────────────
    try:
        alert_name = payload["alerts"][0]["labels"].get("alertname", "UnknownAlert")
    except (KeyError, IndexError):
        alert_name = "UnknownAlert"

    print(f"[RCA Service]   Alert name: {alert_name}")
    print("=" * 60)

    # ── Step 1: Collect evidence ──────────────────────────────────────────
    print("\n[Step 1] Collecting evidence...")
    evidence = collect_evidence(payload)

    # ── Step 2: RAG — find similar past incidents ─────────────────────────
    print("\n[Step 2] Running RAG retrieval (LangChain + FAISS)...")
    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    rag_query  = (
        f"BAT model recall drop battery_status null values "
        f"demand_type={evidence.get('demand_type', 'BAT')} "
        f"feature drift data quality pipeline"
    )
    rag_context = retrieve_similar_incidents(rag_query, gemini_key)

    # ── Step 3: Generate RCA report with Gemini ───────────────────────────
    print("\n[Step 3] Calling Gemini LLM to generate RCA report...")
    report = generate_rca_report(evidence, rag_context)

    # ── Step 4: Save report to outputs/ ──────────────────────────────────
    print("\n[Step 4] Saving report...")
    report_path = save_report(report, OUTPUT_DIR)

    # ── Step 5: Send email ────────────────────────────────────────────────
    print("\n[Step 5] Sending email...")
    email_status = send_email(report, alert_name)

    # ── Done ──────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"[RCA Service] ✓ Pipeline complete!")
    print(f"[RCA Service]   Report : {report_path}")
    print(f"[RCA Service]   Email  : {email_status}")
    print(f"{'='*60}\n")

    return JSONResponse({
        "status":       "success",
        "alert_name":   alert_name,
        "report_path":  report_path,
        "email_status": email_status,
        "timestamp":    datetime.now(timezone.utc).isoformat(),
    })


@app.get("/")
def root():
    return {
        "message": "AI RCA Agent is running.",
        "endpoints": {
            "health":      "GET  /health",
            "trigger_rca": "POST /trigger-rca",
            "api_docs":    "GET  /docs",
        }
    }
