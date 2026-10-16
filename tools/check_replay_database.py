"""Check observed real capture IDs in InfluxDB, including old backfill timestamps."""
import argparse,json,re,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--input',default='output/requirements_audit_20261009/replay_usb_20261010.json');p.add_argument('--output',default='output/requirements_audit_20261009/replay_database_20261010.json');a=p.parse_args()
observed=json.loads((ROOT/a.input).read_text())
ids=sorted({s['id'] for s in observed['samples'] if re.fullmatch(r'[a-f0-9]{8}-[a-f0-9]{8}',s['id']) and isinstance(s.get('timestamp'),int) and s['timestamp']>=1704067200})
if not ids:raise SystemExit('No observed capture IDs with trusted time to check')
token=re.search(r'INFLUX_TOKEN\[\]\s*=\s*"([^"\n]+)"',(ROOT/'include/config.h').read_text(encoding='utf8'))[1]
sql="SELECT sample_id, COUNT(*) AS rows FROM ku_watch WHERE sample_id IN ("+','.join("'"+i+"'" for i in ids)+") GROUP BY sample_id"
req=urllib.request.Request('http://127.0.0.1:8181/api/v3/query_sql',data=json.dumps({'db':'iot','q':sql,'format':'json'}).encode(),headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with opener.open(req,timeout=10) as response:rows=json.load(response)
found={r['sample_id']:r['rows'] for r in rows}
with opener.open('http://127.0.0.1:8871/status',timeout=5) as response:spool=json.load(response)
result={'boundary':'Only actual capture IDs observed over MQTT; historical timestamps included','observed':len(ids),'stored_once':sum(found.get(i)==1 for i in ids),'missing':[i for i in ids if i not in found],'duplicates':[i for i in ids if found.get(i,0)>1],'spool':spool,'passed':bool(ids) and all(found.get(i)==1 for i in ids)}
(ROOT/a.output).write_text(json.dumps(result,indent=2));print(json.dumps(result))
