# AI RCA Agent Demo — MLOps Monitoring with LangChain + FAISS + Gemini

Automated Root Cause Analysis system for MLOps model monitoring.
When BAT model recall drops below 0.55, Prometheus detects it, Alertmanager
triggers a FastAPI webhook, LangChain + FAISS retrieves similar past incidents,
Gemini generates a full RCA report, and the report is emailed to you.

---

## Architecture

```
data/metrics_data.json
        │
        ▼
app/metrics_exporter.py  (Python, port 8001)
  Reads JSON, exposes Prometheus metrics
        │  scrape every 15s
        ▼
Prometheus  (Docker, port 9090)
  Stores time-series data
  Evaluates alert rule: model_recall{BAT} < 0.55
        │  alert fires after 15s
        ▼
Alertmanager  (Docker, port 9093)
  Receives firing alert
  Sends HTTP POST to FastAPI
        │  webhook POST /trigger-rca
        ▼
app/rca_service.py  FastAPI  (Python, port 8000)
        │
        ├── evidence_collector.py  → reads metrics, drift, grafana JSON files
        │
        ├── rag_retriever.py       → LangChain loads incident .md files
        │                             Gemini embeddings → FAISS vector DB
        │                             Semantic search → top 2 similar incidents
        │
        ├── report_generator.py   → Gemini LLM generates structured RCA report
        │
        ├── outputs/rca_report.md  → report saved to disk
        │
        └── email_sender.py       → Gmail SMTP sends HTML email
                │
                ▼
        Grafana  (Docker, port 3000)
          Visualizes Prometheus metrics in real-time dashboards
```

---

## What is Real vs Mock

| Component | Status | Detail |
|---|---|---|
| Prometheus scraping | ✅ Real | Actual Prometheus instance in Docker |
| Alertmanager routing | ✅ Real | Actual Alertmanager sends real webhook |
| FastAPI endpoint | ✅ Real | Real HTTP server receives the webhook |
| LangChain + FAISS | ✅ Real | Real vector DB, real semantic search |
| Gemini embeddings | ✅ Real | Real API call to Google embedding model |
| Gemini LLM report | ✅ Real | Real API call generates the RCA text |
| Gmail email | ✅ Real | Real SMTP delivery |
| Grafana dashboard | ✅ Real | Real Grafana with auto-provisioned dashboard |
| Metric values (0.48) | 🟡 Mock | Hardcoded in metrics_data.json |
| Drift report | 🟡 Mock | Pre-written drift_report.json |
| Grafana snapshot | 🟡 Mock | Pre-written grafana_snapshot.json |
| Past incidents | 🟡 Mock | Two .md files in data/incidents/ |
| ML model itself | ❌ Not present | Only monitoring — no model code |

---

## Prerequisites — What to Install

### Step 1 — Install Python 3.11

**Windows:**
1. Go to https://www.python.org/downloads/
2. Download Python 3.11.x (not 3.13 — some packages have issues)
3. Run the installer
4. ✅ CHECK "Add Python to PATH" on the first screen — critical
5. Click Install Now
6. Open a new PowerShell window and verify:
   ```powershell
   python --version
   # should print: Python 3.11.x
   ```

**Mac:**
```bash
brew install python@3.11
python3 --version
```

---

### Step 2 — Install Docker Desktop

Docker Desktop installs Docker + Docker Compose together.
Prometheus, Alertmanager, and Grafana run as Docker containers.
You do NOT install them separately.

1. Go to https://www.docker.com/products/docker-desktop/
2. Download for your OS (Windows/Mac/Linux)
3. Run the installer — accept all defaults
4. Start Docker Desktop from your Applications/Start menu
5. Wait for the whale icon in the taskbar to stop animating
6. Verify in terminal:
   ```bash
   docker --version
   docker compose version
   ```

---

### Step 3 — Install Git

**Windows:** https://git-scm.com/download/win — accept all defaults
**Mac:** `brew install git` or it comes with Xcode Command Line Tools

---

### Step 4 — Install VS Code (recommended editor)

https://code.visualstudio.com/
Install the Python extension from the Extensions panel.

---

## Project Setup (do once)

### Step 5 — Get the project files

```bash
# If you cloned from GitHub:
git clone https://github.com/YOUR_USERNAME/ai-rca-agent-demo.git
cd ai-rca-agent-demo

# If you unzipped the project:
cd ai-rca-agent-demo
```

---

### Step 6 — Create Python virtual environment

A virtual environment keeps project packages separate from your system Python.

**Mac / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows PowerShell:**
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

If PowerShell blocks the activation script:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
venv\Scripts\Activate.ps1
```

You'll see `(venv)` at the start of your prompt. This means it's active.

---

### Step 7 — Install Python packages

```bash
pip install -r requirements.txt
```

This installs: fastapi, uvicorn, prometheus-client, langchain, faiss-cpu,
google-generativeai, langchain-google-genai, and others.

Takes 2-3 minutes. You'll see lots of output — that's normal.

---

### Step 8 — Get your Gemini API Key (free, 2 minutes)

1. Go to https://aistudio.google.com/app/apikey
2. Sign in with your Google account
3. Click **"Create API Key"**
4. Copy it — looks like: `AIzaSyAbCdEf123...`

---

### Step 9 — Get your Gmail App Password (3 minutes)

Your normal Gmail password won't work in scripts for security reasons.
You need a special App Password.

1. Go to https://myaccount.google.com
2. Click **Security** in the left menu
3. Scroll to **"2-Step Verification"** and make sure it is **ON**
   (You must enable this first — App Passwords require it)
4. In the search bar at the top of the page, type **"App passwords"**
5. Click the result
6. Under "App name", type: `RCA Agent`
7. Click **Create**
8. Google shows a 16-character password like: `abcd efgh ijkl mnop`
9. Copy it exactly as shown (spaces are OK)

---

### Step 10 — Create your .env file

```bash
cp .env.example .env
```

Open `.env` in VS Code and fill in your 4 values:

```
GEMINI_API_KEY=AIzaSy...your-actual-key
EMAIL_SENDER=youremail@gmail.com
EMAIL_APP_PASSWORD=abcd efgh ijkl mnop
EMAIL_RECEIVER=abc@gmail.com
```

Save the file. The `.env` file is in `.gitignore` — it will never be committed.

---

## Running the Project

You need **3 terminal windows** open at the same time.

---

### Terminal 1 — Start Docker services (Prometheus + Alertmanager + Grafana)

```bash
cd ai-rca-agent-demo
docker compose up
```

**Windows PowerShell:**
```powershell
cd ai-rca-agent-demo
docker compose up
```

Wait until you see these lines (takes about 30 seconds):
```
prometheus   | Server is ready to receive web requests.
alertmanager | Listening address=0.0.0.0:9093
grafana      | HTTP Server Listen address=0.0.0.0:3000
```

Leave this terminal running. Do not close it.

---

### Terminal 2 — Start the metrics exporter

Open a new terminal window.

**Mac / Linux:**
```bash
cd ai-rca-agent-demo
source venv/bin/activate
python app/metrics_exporter.py
```

**Windows PowerShell:**
```powershell
cd ai-rca-agent-demo
venv\Scripts\Activate.ps1
python app\metrics_exporter.py
```

You should see:
```
[Exporter] ✓ Metrics server running at http://localhost:8001/metrics
[Exporter]   Prometheus will scrape this every 15 seconds.
[Exporter]   BAT recall = 0.48 → alert will fire after ~15 seconds
[Exporter] Updated metrics — BAT recall=0.48
```

Leave this terminal running.

---

### Terminal 3 — Start the FastAPI RCA service

Open a third terminal window.

**Mac / Linux:**
```bash
cd ai-rca-agent-demo
source venv/bin/activate
uvicorn app.rca_service:app --host 0.0.0.0 --port 8000 --reload
```

**Windows PowerShell:**
```powershell
cd ai-rca-agent-demo
venv\Scripts\Activate.ps1
uvicorn app.rca_service:app --host 0.0.0.0 --port 8000 --reload
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

Leave this terminal running.

---

## Verify Everything is Working

### Check metrics are being served
Open: http://localhost:8001/metrics

Look for:
```
model_recall{demand_type="BAT"} 0.48
model_precision{demand_type="BAT"} 0.6
api_error_rate 0.01
api_latency_p95_ms 180.0
```

### Check Prometheus is scraping
Open: http://localhost:9090/targets

You should see two targets:
- `prometheus` — State: UP (green)
- `mlops_metrics` — State: UP (green)

If `mlops_metrics` shows DOWN, check that Terminal 2 (metrics exporter) is running.

### Check the alert is firing
Open: http://localhost:9090/alerts

After about 30 seconds you should see:
- `BATRecallDrop` — State: **FIRING** (red background)

It goes through two stages:
1. **PENDING** (yellow) — rule matched but `for: 15s` hasn't elapsed yet
2. **FIRING** (red) — alert is active, Alertmanager receives it

### Check Alertmanager received it
Open: http://localhost:9093

You should see the `BATRecallDrop` alert listed as active.

### Check FastAPI received the webhook
Look at Terminal 3 output. After the alert fires you should see:
```
============================================================
[RCA Service] ← Webhook received from Alertmanager
[Step 1] Collecting evidence...
[Step 2] Running RAG retrieval (LangChain + FAISS)...
[RAG] Building FAISS index from incident files (first run)...
[RAG] ✓ FAISS index built and saved to vector_store/faiss_index
[Step 3] Calling Gemini LLM to generate RCA report...
[Gemini] ✓ Report received (2,841 characters).
[Step 4] Saving report...
[Step 5] Sending email...
[Email] ✓ Report sent to abc@gmail.com
[RCA Service] ✓ Pipeline complete!
============================================================
```

### Check the RCA report
```bash
cat outputs/rca_report.md
```

You'll see the full Markdown report with 8 sections.

---

## Grafana — Where to See the Graphs

Grafana is a dashboard tool that visualises your Prometheus metrics.

### Open Grafana
1. Go to: http://localhost:3000
2. Login screen appears
3. Username: `admin`
4. Password: `admin`
5. Grafana may ask you to change the password — click "Skip" for now

### View the MLOps Dashboard
1. Click the **four-squares icon** (Dashboards) in the left sidebar
   Or go to: http://localhost:3000/dashboards
2. Click on the folder **"MLOps"**
3. Click **"MLOps Model Monitoring"**
4. You see 6 panels:

| Panel | What it shows |
|---|---|
| **BAT Model Recall** | Gauge: current recall value (red = below 0.55) |
| **BAT Model Precision** | Gauge: current precision |
| **API Latency p95 (ms)** | Gauge: p95 latency |
| **API Error Rate** | Gauge: error rate |
| **BAT Recall Over Time** | Time-series graph of recall trend |
| **Prediction Volume** | Time-series of prediction count |

### What you should see
- BAT Recall gauge is **red** (0.48, below the 0.55 threshold)
- The time-series graph shows recall staying at 0.48

### Making the alert "resolve" (optional)
To see what recovery looks like:
1. Edit `data/metrics_data.json`
2. Change `"model_recall_bat": 0.48` to `"model_recall_bat": 0.72`
3. Save the file
4. Within 15 seconds, metrics_exporter.py reads the new value
5. Prometheus picks it up, alert goes from FIRING → RESOLVED
6. Grafana gauge turns green

### Adding your own panel
1. Click the **+** button → Dashboard → Add visualization
2. In the query box, type: `model_recall{demand_type="BAT"}`
3. Click **Run queries**
4. Choose panel type: Time series, Gauge, Stat, etc.
5. Click **Apply** then **Save dashboard**

---

## Manually Test the RCA Trigger

You can send a test webhook without waiting for the alert to fire:

**Mac / Linux:**
```bash
curl -X POST http://localhost:8000/trigger-rca \
  -H "Content-Type: application/json" \
  -d '{
    "version": "4",
    "status": "firing",
    "alerts": [{
      "status": "firing",
      "labels": {
        "alertname": "BATRecallDrop",
        "demand_type": "BAT",
        "severity": "warning"
      },
      "annotations": {
        "summary": "BAT recall dropped below threshold",
        "description": "BAT model recall is below 0.55 and requires RCA investigation."
      },
      "startsAt": "2024-01-15T10:20:00Z"
    }]
  }'
```

**Windows PowerShell:**
```powershell
$body = @{
  version = "4"
  status  = "firing"
  alerts  = @(@{
    status      = "firing"
    labels      = @{ alertname = "BATRecallDrop"; demand_type = "BAT"; severity = "warning" }
    annotations = @{ summary = "BAT recall dropped below threshold" }
    startsAt    = "2024-01-15T10:20:00Z"
  })
} | ConvertTo-Json -Depth 5

Invoke-RestMethod -Uri "http://localhost:8000/trigger-rca" `
  -Method POST `
  -ContentType "application/json" `
  -Body $body
```

You should get:
```json
{
  "status": "success",
  "alert_name": "BATRecallDrop",
  "report_path": "outputs/rca_report_20240115_102542.md",
  "email_status": "sent",
  "timestamp": "2024-01-15T10:25:42Z"
}
```

---

## Check the FastAPI Docs

FastAPI auto-generates interactive API documentation.

Open: http://localhost:8000/docs

You can see and test both endpoints:
- `GET  /health`
- `POST /trigger-rca`

---

## Project Structure

```
ai-rca-agent-demo/
│
├── app/
│   ├── metrics_exporter.py   ← reads metrics_data.json, serves :8001/metrics
│   ├── rca_service.py        ← FastAPI, POST /trigger-rca, orchestrates pipeline
│   ├── evidence_collector.py ← reads the 3 JSON evidence files
│   ├── rag_retriever.py      ← LangChain + FAISS + Gemini embeddings
│   ├── report_generator.py   ← Gemini LLM, structured 8-section RCA report
│   ├── email_sender.py       ← Gmail SMTP, HTML email
│   └── utils.py              ← .env loader, file saver, helpers
│
├── data/
│   ├── metrics_data.json          ← mock metric values (edit to test)
│   ├── drift_report.json          ← mock feature drift data
│   ├── grafana_snapshot.json      ← mock Grafana observation
│   └── incidents/
│       ├── incident_001_battery_nulls.md  ← past incident (RAG knowledge base)
│       └── incident_002_api_latency.md    ← past incident (RAG knowledge base)
│
├── monitoring/
│   ├── prometheus.yml        ← scrape config, points to :8001
│   ├── alert_rules.yml       ← BATRecallDrop rule (recall < 0.55 for 15s)
│   ├── alertmanager.yml      ← routes to FastAPI :8000/trigger-rca
│   └── grafana/
│       ├── datasource.yml    ← auto-connects Grafana to Prometheus
│       ├── dashboard.yml     ← tells Grafana where dashboard JSON is
│       └── mlops_dashboard.json  ← 6-panel dashboard definition
│
├── outputs/                  ← generated RCA reports saved here
├── vector_store/             ← FAISS index saved here (auto-created)
├── docker-compose.yml        ← Prometheus + Alertmanager + Grafana
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## Troubleshooting

**Prometheus shows mlops_metrics target as DOWN**
- Check Terminal 2 is running the metrics exporter
- Check: http://localhost:8001/metrics — should show metric lines
- On Linux: `host.docker.internal` may not work — replace with your machine's IP in `monitoring/prometheus.yml`
  ```yaml
  targets: ["192.168.1.x:8001"]   # use your local IP
  ```
  Find your IP: `ip addr show` (Linux) or `ipconfig` (Windows)

**Alert stays in PENDING, never goes to FIRING**
- Wait at least 30 seconds — the rule has `for: 15s`
- Check Prometheus targets are UP first

**FastAPI not receiving webhook**
- Confirm Terminal 3 (uvicorn) is running
- Check: http://localhost:8000/health
- Check Alertmanager logs: `docker compose logs alertmanager`

**Gemini API error**
- Check `.env` has `GEMINI_API_KEY` set (not the placeholder)
- The free tier has a limit of 60 requests/minute — wait and retry

**Email not sending**
- Use App Password — NOT your normal Gmail password
- 2-Step Verification must be ON before creating App Password
- Check `.env` has all 3 email vars set

**FAISS index error on second run**
- Delete `vector_store/faiss_index/` folder and re-run — it will rebuild

**Port already in use**
```bash
docker compose down
# then restart
docker compose up
```
---

## Future Enhancements

| Enhancement | What it adds |
|---|---|
| AWS Lambda + API Gateway | Replaces FastAPI — fully serverless, no server to manage |
| S3 for report storage | Reports stored centrally, accessible by whole team |
| ChromaDB / Pinecone | Managed vector DB, scales to thousands of incidents |
| Real drift monitoring (Evidently) | Replaces mock drift_report.json with real PSI calculations |
| Slack / PagerDuty integration | Alert the on-call engineer in Slack with report link |
| Scheduled retraining trigger | If RCA says "RETRAIN", auto-trigger SageMaker training job |
| Multi-model support | Monitor DAILY, WEEKLY models with same pipeline |
