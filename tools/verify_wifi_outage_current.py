"""Bounded real Wi-Fi outage via existing NETPAUSE; restore even on errors."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,subprocess,time,urllib.request
from activity_export import Watch
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/final_acceptance_20261016/offline_10min';OUT.mkdir(parents=True,exist_ok=True)
NODE=Path('C:/Users/pomma/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe')
target=OUT/'result.json'
if target.exists():raise FileExistsError('Preserve previous outage')
pause_s=620
r={'started_utc':datetime.now(timezone.utc).isoformat(),'boundary':'Actual Wi-Fi disconnect of this watch only via NETPAUSE620; shared hotspot/broker unchanged; no generated telemetry. Read only sample IDs, timing and queue/sensor health.','requested_pause_s':pause_s,'states':[],'restored':False,'passed':False}
watch=Watch('COM15');observer=None;changed=False
def stamp():return datetime.now(timezone.utc).isoformat()
def save():
 (OUT/'progress.json').write_text(json.dumps(r,indent=2),encoding='utf8')
def query(command,window=.45):
 watch.send(command);end=time.monotonic()+window;got=[]
 while time.monotonic()<end:
  line=watch.serial.readline().decode('ascii','replace').strip()
  if line.startswith(('NETWORK ','QUEUE ','CLOCK ','SENSORS ','SCREEN ','NETPAUSE ')):got.append(line)
 return got
def state():
 d={'queried_utc':stamp()}
 for command in ['NETINFO','SENSORINFO','CLOCKINFO','SCREENINFO']:
  for line in query(command):
   prefix=line.split()[0]
   for k,v in re.findall(r'(\w+)=([^ ]+)',line):
    if prefix=='SENSORS' and k not in ['gas','iaq','accuracy','stable','runin','bsec','ina','heap']:continue
    if prefix=='SCREEN' and k not in ['frames','page','painted']:continue
    if prefix=='CLOCK' and k not in ['utc','valid','source','uptime']:continue
    d[(prefix.lower()+'_'+k)]=float(v) if re.fullmatch(r'-?\d+\.\d+',v) else int(v) if re.fullmatch(r'-?\d+',v) else v
 return d
try:
 active=watch.status();assert not active['active'],'Active WALK'
 observer=subprocess.Popen([str(NODE),str(ROOT/'tools/observe_replay.cjs'),str(OUT/'received.json'),'1800000'],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
 time.sleep(3);drain_deadline=time.monotonic()+90
 while True:
  r['before']=state();b=r['before']
  if b.get('network_wifi')==b.get('network_mqtt')==1 and b.get('queue_pending',999)<=2:break
  if time.monotonic()>drain_deadline:raise RuntimeError('Initial online queue did not drain')
  print(json.dumps({'phase':'prepare','pending':b.get('queue_pending')}),flush=True);time.sleep(3)
 assert b.get('network_wifi')==b.get('network_mqtt')==1,'Watch must be online'
 needed=(b.get('queue_max_encoded',512)+80)*(pause_s+20)+b.get('queue_reserve',131072)
 assert b.get('queue_free',0)>needed,'Insufficient safe flash capacity for bounded test'
 assert b.get('queue_pending',99)<=2,'Existing queue must drain first'
 r['capacity_check']={'needed_bytes':needed,'free_bytes':b['queue_free']};r['pause_command_utc']=stamp();query('NETPAUSE '+str(pause_s),.3);changed=True;began=time.monotonic();last_print=-30
 while time.monotonic()-began<pause_s+4:
  now=time.monotonic();s=state();s['at_s']=round(time.monotonic()-began,3);r['states'].append(s);save()
  if s.get('queue_dropped')!=b.get('queue_dropped') or s.get('queue_errors')!=b.get('queue_errors'):raise RuntimeError('Queue health changed; stop fault and recover')
  if now-began-last_print>=29:print(json.dumps({'phase':'offline_test','elapsed_s':round(now-began),'pending':s.get('queue_pending'),'wifi':s.get('network_wifi'),'mqtt':s.get('network_mqtt')}),flush=True);last_print=now-began
  time.sleep(max(0,min(8,pause_s+4-(time.monotonic()-began))))
 offline=[s for s in r['states'] if s.get('network_wifi')==0 and s.get('network_mqtt')==0]
 r['observed_offline_span_s']=offline[-1]['at_s']-offline[0]['at_s'] if offline else 0
 r['main_loop_progressed']=len(offline)>1 and offline[-1].get('clock_uptime',0)>offline[0].get('clock_uptime',0)
 r['sensor_queries_answered_during_outage']=bool(offline) and all('sensors_bsec' in s and 'sensors_ina' in s for s in offline)
 query('NETPAUSE 0');changed=False;r['resume_command_utc']=stamp();r['restored']=True
 deadline=time.monotonic()+720
 while time.monotonic()<deadline:
  s=state();r['after']=s;save()
  if s.get('network_wifi')==s.get('network_mqtt')==1 and s.get('queue_pending',999)<=2:break
  print(json.dumps({'phase':'recovery','pending':s.get('queue_pending'),'wifi':s.get('network_wifi'),'mqtt':s.get('network_mqtt')}),flush=True);time.sleep(10)
 else:raise RuntimeError('Automatic recovery did not finish within bounded window')
 time.sleep(3);observer.terminate();observer.wait(timeout=5);observer=None
 records=json.loads((OUT/'received.json').read_text());unique={p['id']:p for p in records['samples'] if re.fullmatch(r'[a-fA-F0-9]{8}-[a-fA-F0-9]{8}',p.get('id',''))}
 sessions={k.split('-')[0] for k in unique};r['sessions']=list(sessions);assert len(sessions)==1,'Unexpected boot during outage'
 first,last=min(unique),max(unique);expected=int(last[9:],16)-int(first[9:],16)+1
 r['received_unique']=len(unique);r['expected_capture_ids']=expected;r['received_missing']=expected-len(unique)
 history=[p for p in unique.values() if p.get('backfill')];r['backfill_unique']=len(history);r['lwt_offline_observed']=any(x.get('online') is False for x in records['statuses']);r['online_status_observed']=any(x.get('online') is True for x in records['statuses'])
 token=re.search(r'INFLUX_TOKEN\[\]\s*=\s*"([^"\n]+)"',(ROOT/'include/config.h').read_text())[1]
 sql="SELECT COUNT(*) AS rows,COUNT(DISTINCT sample_id) AS captures FROM ku_watch WHERE sample_id >= '"+first+"' AND sample_id <= '"+last+"'"
 for _ in range(25):
  req=urllib.request.Request('http://127.0.0.1:8181/api/v3/query_sql',data=json.dumps({'db':'iot','q':sql,'format':'json'}).encode(),headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
  with urllib.request.urlopen(req,timeout=8) as response:counts=json.load(response)[0]
  if counts['rows']==counts['captures']==expected:break
  time.sleep(2)
 r['database_capture_range']={'first':first,'last':last,'expected':expected,**counts};r['database_complete']=counts['rows']==counts['captures']==expected
 r['backfill_has_trusted_time']=all(isinstance(p.get('timestamp'),int) and p['timestamp']>=1704067200 for p in history)
 r['passed']=r['observed_offline_span_s']>=600 and r['main_loop_progressed'] and r['sensor_queries_answered_during_outage'] and r['received_missing']==0 and r['backfill_unique']>=600 and r['database_complete'] and r['backfill_has_trusted_time'] and r['after']['queue_dropped']==b['queue_dropped'] and r['after']['queue_errors']==b['queue_errors']
except Exception as e:r.update(error=type(e).__name__,reason=str(e)[:200])
finally:
 if changed:
  try:query('NETPAUSE 0');r['restored']=True
  except Exception:r['restored']=False
 watch.close()
 if observer:
  observer.terminate()
  try:observer.wait(timeout=5)
  except Exception:pass
 r['finished_utc']=stamp();save();target.write_text(json.dumps(r,indent=2),encoding='utf8');print(json.dumps({k:v for k,v in r.items() if k!='states'}),flush=True)
raise SystemExit(0 if r['passed'] else 1)
