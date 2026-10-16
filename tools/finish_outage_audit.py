"""Continue recovery of the already completed outage, without repeating the fault.
The first observation window is preserved; SQL checks every capture in its session
from the first observed ID through a fresh post-recovery MQTT observation.
"""
import base64,datetime,json,re,subprocess,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/requirements_audit_20261009'
report=json.loads((OUT/'broker_outage.json').read_text())
if not report['restored']:raise RuntimeError('Restore the saved endpoint before auditing recovery')
report['initial_recovery_window']={k:report.get(k) for k in ['after','received_unique','backfill_unique','missing_sequences','passed']}
saved=json.loads((ROOT/'config/watch-access.local.json').read_text())
auth='Basic '+base64.b64encode((saved['username']+':'+saved['password']).encode()).decode()
def status():
    with urllib.request.urlopen(urllib.request.Request(saved['url'].rstrip('/')+'/status',headers={'Authorization':auth}),timeout=8) as response:return json.load(response)
started=time.monotonic()
while True:
    current=status()
    if current['wifi'] and current['mqtt'] and current['pending']<=2:break
    if time.monotonic()-started>600:raise RuntimeError('Recovery queue still pending after another ten minutes')
    print('Recovery pending',current['pending'],flush=True);time.sleep(5)
subprocess.run(['C:/Program Files/nodejs/node.exe',str(ROOT/'tools/observe_replay.cjs'),str(OUT/'broker_recovery_observer.json'),'6000'],cwd=ROOT,check=True)
packets=json.loads((OUT/'broker_replay.json').read_text())['samples']+json.loads((OUT/'broker_recovery_observer.json').read_text())['samples']
ids=[p['id'].lower() for p in packets if re.fullmatch(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{8}',p.get('id',''))]
sessions={key[:8] for key in ids}
if len(sessions)!=1:raise RuntimeError('Unexpected restart during recovery')
first,last=min(ids),max(ids)
expected=int(last[9:],16)-int(first[9:],16)+1
token=re.search(r'INFLUX_TOKEN\[\]\s*=\s*"([^"\n]+)"',(ROOT/'include/config.h').read_text(encoding='utf8'))[1]
fault_start=datetime.datetime.fromtimestamp(report['started_utc'],datetime.timezone.utc).isoformat()
fault_end=datetime.datetime.fromtimestamp(report['started_utc']+report['observed_seconds'],datetime.timezone.utc).isoformat()
sql="SELECT COUNT(*) AS rows, COUNT(DISTINCT sample_id) AS captures, SUM(CASE WHEN time >= '"+fault_start+"' AND time < '"+fault_end+"' THEN 1 ELSE 0 END) AS outage_captures FROM ku_watch WHERE sample_id >= '"+first+"' AND sample_id <= '"+last+"'"
for attempt in range(30):
    req=urllib.request.Request('http://127.0.0.1:8181/api/v3/query_sql',data=json.dumps({'db':'iot','q':sql,'format':'json'}).encode(),headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=8) as response:counts=json.load(response)[0]
    if counts['captures']==expected:break
    time.sleep(1)
report['after']=current
report['recovery_verified_utc']=time.time()
report['database_capture_range']={'first':first,'last':last,'expected':expected,**counts}
report['database_rows']=counts['rows'];report['database_distinct_captures']=counts['captures']
report['database_outage_captures']=counts['outage_captures'];report['missing_sequences']=expected-counts['captures']
report['database_complete']=counts['rows']==counts['captures']==expected
report['recovery_boundary']='Original subscriber stopped after 120s while queue remained. Continued recovery checks SQL for every sequential capture through a fresh MQTT observation; no second outage was induced.'
report['passed']=not report.get('error') and report['observed_seconds']>=600 and report['database_complete'] and counts['outage_captures']>=597 and current['pending']<=2 and current['dropped']==report['before']['dropped'] and current['storage_errors']==report['before']['storage_errors']
(OUT/'broker_outage.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='states'}))
raise SystemExit(0 if report['passed'] else 1)
