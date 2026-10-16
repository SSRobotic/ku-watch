"""Coordinated, reversible MQTT topic change using the watch's existing NVS form."""
from pathlib import Path
from datetime import datetime,timezone
import base64,html,json,re,subprocess,time,urllib.request,urllib.parse
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/final_acceptance_20261016'
NODE=Path('C:/Users/pomma/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe')
plan=json.loads((OUT/'topic_plan.json').read_text());assert plan['reader_subscription_allowed']
report={'started_utc':datetime.now(timezone.utc).isoformat(),'old_topic':plan['old_topic'],'new_topic':plan['new_topic'],'configuration_only':True,'firmware_unchanged':True,'restored_on_failure':False}
if (OUT/'topic_migration.json').exists():raise FileExistsError('Keep earlier migration')
access=json.loads((ROOT/'config/watch-access.local.json').read_text());url=access['url'].rstrip('/')
auth='Basic '+base64.b64encode((access['username']+':'+access['password']).encode()).decode()
def watch(route,data=None):
 req=urllib.request.Request(url+'/'+route,data=data,headers={'Authorization':auth})
 with urllib.request.urlopen(req,timeout=10) as r:return r.read()
def fields():return {k:html.unescape(v) for k,v in re.findall(r"name='([^']+)'[^>]*value=\"([^\"]*)\"",watch('').decode())}
def save_watch(values):
 form=dict(values);form['token']=access['password'];watch('save',urllib.parse.urlencode(form).encode())
def runtime():
 with urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:1880/flows',headers={'Node-RED-API-Version':'v2'}),timeout=8) as r:return json.load(r)
def deploy(nodes):
 current=runtime();current['flows']=nodes
 req=urllib.request.Request('http://127.0.0.1:1880/flows',data=json.dumps(current).encode(),method='POST',headers={'Content-Type':'application/json','Node-RED-API-Version':'v2','Node-RED-Deployment-Type':'nodes'})
 with urllib.request.urlopen(req,timeout=15) as r:r.read()
before=fields();state=json.loads(watch('status'));assert state['wifi'] and state['mqtt'] and not state['recording']
original=runtime()['flows'];cloud_file=ROOT/'config/cloud.local.json';cloud_raw=cloud_file.read_bytes();cloud=json.loads(cloud_raw)
backup=ROOT/'config/topic-migration-backup.local.json';backup.write_text(json.dumps({'fields':before,'flows':original,'old_topic':plan['old_topic']}),encoding='utf8')
changed=False
try:
 flows=json.loads(json.dumps(original));matches=[n for n in flows if n.get('id')=='ku_cloud_input' and n.get('type')=='mqtt in'];assert len(matches)==1
 matches[0]['topic']=plan['new_topic'];matches[0]['qos']='1';deploy(flows);changed=True
 after=dict(before);after['topic']=plan['new_topic'];save_watch(after)
 cloud['topic']=plan['new_topic'];cloud_file.write_text(json.dumps(cloud,indent=2),encoding='utf8')
 subprocess.run([str(NODE),str(ROOT/'tools/wait_configured_topic.cjs'),'output/final_acceptance_20261016/topic_transport.json'],cwd=ROOT,check=True,timeout=55,stdout=subprocess.DEVNULL)
 observed=json.loads((OUT/'topic_transport.json').read_text());ids=[x['sample_id'] for x in observed['samples']];assert all(re.fullmatch('[a-fA-F0-9]{8}-[a-fA-F0-9]{8}',x) for x in ids)
 token=re.search(r'INFLUX_TOKEN\[\]\s*=\s*"([^"\n]+)"',(ROOT/'include/config.h').read_text())[1]
 q='SELECT COUNT(*) AS rows,COUNT(DISTINCT sample_id) AS captures FROM ku_watch WHERE sample_id IN ('+','.join("'"+x+"'" for x in ids)+')'
 for _ in range(15):
  req=urllib.request.Request('http://127.0.0.1:8181/api/v3/query_sql',data=json.dumps({'db':'iot','q':q,'format':'json'}).encode(),headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
  with urllib.request.urlopen(req,timeout=8) as r:counts=json.load(r)[0]
  if counts['rows']==counts['captures']==len(ids):break
  time.sleep(1)
 assert counts['rows']==counts['captures']==len(ids),'New canonical stream did not reach DB exactly once'
 readback=fields();assert readback['topic']==plan['new_topic'];assert all(readback[k]==v for k,v in before.items() if k!='topic')
 portable=ROOT/'integration/node-red/ku-watch-cloud-flow.json';data=json.loads(portable.read_text(encoding='utf-8-sig'))
 for n in data:
  if n.get('id')=='ku_cloud_input':n['topic']=plan['new_topic'];n['qos']='1'
 portable.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 for config in [ROOT/'include/config.h',ROOT/'include/config.example.h']:
  s=config.read_text(encoding='utf8');s,n=re.subn(r'(constexpr char MQTT_TOPIC\[\]\s*=\s*)"[^"\n]*"',lambda m:m[1]+'"'+plan['new_topic']+'"',s);assert n==1;config.write_text(s,encoding='utf8')
 report.update(passed=True,other_form_fields_unchanged=True,database=counts,status_before=state,status_after=json.loads(watch('status')))
except Exception as e:
 report.update(passed=False,error=type(e).__name__,reason=str(e)[:160])
 if changed:
  try:save_watch(before);deploy(original);cloud_file.write_bytes(cloud_raw);report['restored_on_failure']=True
  except Exception as restore:report['restore_error']=type(restore).__name__
finally:
 report['finished_utc']=datetime.now(timezone.utc).isoformat();(OUT/'topic_migration.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report))
raise SystemExit(0 if report.get('passed') else 1)
