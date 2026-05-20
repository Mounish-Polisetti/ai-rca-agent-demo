# Incident: API Latency Spike

## Alert
API latency p95 exceeded 500ms threshold. Alert: APILatencyHigh fired.

## Root Cause
EC2 instance CPU utilization increased to 95% due to sudden high request
volume from a batch prediction job running during peak hours.

## Resolution
Scaled API service horizontally (added 2 instances), optimized batch
request handling with queue-based processing.

## Timeline
- 14:00 UTC: Batch prediction job triggered with 3x normal volume
- 14:05 UTC: CPU utilization on API EC2 spiked to 95%
- 14:10 UTC: p95 latency crossed 500ms threshold
- 14:12 UTC: AlertManager fired APILatencyHigh
- 14:30 UTC: Scaled API to 3 instances
- 14:45 UTC: Latency returned to normal (p95 = 180ms)

## Action Taken
Infrastructure scaling was required. Model retraining was not required.
Batch jobs now scheduled during off-peak hours.

## Tags
API, latency, EC2, scaling, service monitoring, infrastructure, batch jobs
