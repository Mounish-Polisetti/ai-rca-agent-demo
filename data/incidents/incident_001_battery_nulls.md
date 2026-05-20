# Incident: BAT Recall Drop Due to Battery Status Nulls

## Alert
BAT recall dropped below threshold (0.55). Alert: BATRecallDrop fired.

## Root Cause
battery_status feature had high null values (28% null rate vs normal 3%)
due to upstream battery data feed delay in the ETL pipeline.

## Resolution
Fixed upstream battery feed, updated Glue mapping, and backfilled missing
feature values. Model retraining was not required.

## Timeline
- 08:00 UTC: Battery data feed delayed due to upstream source issue
- 09:30 UTC: Null rate in battery_status rose from 3% to 28%
- 10:15 UTC: BAT recall dropped from 0.64 to 0.47
- 10:20 UTC: Alertmanager fired BATRecallDrop alert
- 11:00 UTC: Root cause identified — upstream feed issue
- 13:00 UTC: Pipeline fix deployed, null rate returned to 3%
- 14:00 UTC: BAT recall recovered to 0.63

## Action Taken
Pipeline fix was done. Model retraining was not required.
Monitoring added for battery_status null rate.

## Tags
BAT, battery_status, null values, data quality, upstream delay, pipeline fix
