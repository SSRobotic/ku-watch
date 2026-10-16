"""Export actual MQTT receipt metadata and a fresh read-only InfluxDB count query."""
import csv
import hashlib
import json
import re
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/measurement_evidence_20261011'
OUT.mkdir(parents=True, exist_ok=True)
source = ROOT / 'output/requirements_audit_20261009/replay_phone_drain_20261010.json'
receipts = json.loads(source.read_text(encoding='utf-8'))
observed = {}
for sample in receipts['samples']:
    sample_id = sample.get('id', '')
    timestamp = sample.get('timestamp')
    if re.fullmatch(r'[a-f0-9]{8}-[a-f0-9]{8}', sample_id) and isinstance(timestamp, int) and timestamp >= 1704067200:
        observed.setdefault(sample_id, sample)
if not observed:
    raise SystemExit('No actual observed IDs to check')
ids = sorted(observed)
token_match = re.search(r'INFLUX_TOKEN\[\]\s*=\s*"([^"\n]+)"', (ROOT / 'include/config.h').read_text(encoding='utf-8'))
if not token_match:
    raise SystemExit('Local InfluxDB credential unavailable')
sql = "SELECT sample_id, COUNT(*) AS rows FROM ku_watch WHERE sample_id IN (" + ','.join("'" + i + "'" for i in ids) + ') GROUP BY sample_id ORDER BY sample_id'
request = urllib.request.Request(
    'http://127.0.0.1:8181/api/v3/query_sql',
    data=json.dumps({'db': 'iot', 'q': sql, 'format': 'json'}).encode(),
    headers={'Authorization': 'Bearer ' + token_match[1], 'Content-Type': 'application/json'})
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
try:
    with opener.open(request, timeout=15) as response:
        database_rows = json.load(response)
except Exception as error:
    raise SystemExit('Read-only database check failed: ' + type(error).__name__)
counts = {r['sample_id']: int(r['rows']) for r in database_rows}
def utc_seconds(value):
    return datetime.fromtimestamp(value, timezone.utc).isoformat()
csv_path = OUT / 'actual_received_657_ids_database_check.csv'
with csv_path.open('w', encoding='utf-8-sig', newline='') as stream:
    writer = csv.writer(stream)
    writer.writerow(['sample_id', 'capture_utc_from_receipt', 'mqtt_received_utc', 'receipt_backfill', 'influx_row_count_at_check', 'stored_exactly_once'])
    for sample_id in ids:
        sample = observed[sample_id]
        received = sample.get('at')
        writer.writerow([sample_id, utc_seconds(sample['timestamp']), utc_seconds(received / 1000) if isinstance(received, (int, float)) else '', sample.get('backfill', ''), counts.get(sample_id, 0), counts.get(sample_id) == 1])
(OUT / 'verification_query.sql').write_text(sql + ';\n', encoding='utf-8')
(OUT / 'influx_query_response.json').write_text(json.dumps(database_rows, indent=2), encoding='utf-8')
now = datetime.now(timezone.utc)
report = {
    'data_type': 'actual_observed_receipts_and_read_only_database_query',
    'checked_utc': now.isoformat(),
    'checked_bangkok': now.astimezone(timezone(timedelta(hours=7))).isoformat(),
    'boundary': 'Rechecks the 657 IDs captured on 10 October; no new watch test, no proof of unobserved captures or 24-hour continuity',
    'observed': len(ids),
    'stored_once': sum(counts.get(i) == 1 for i in ids),
    'missing': [i for i in ids if i not in counts],
    'duplicates': [i for i in ids if counts.get(i, 0) > 1],
    'passed_for_observed_set': all(counts.get(i) == 1 for i in ids),
    'source_receipts': str(source.relative_to(ROOT)),
    'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
    'outputs': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [csv_path, OUT / 'verification_query.sql', OUT / 'influx_query_response.json']},
}
(OUT / 'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({k: report[k] for k in ['checked_bangkok', 'observed', 'stored_once', 'missing', 'duplicates', 'passed_for_observed_set']}, ensure_ascii=False))
