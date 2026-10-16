"""Provision a Grafana dashboard from actual received IDs and saved measured delays."""
from pathlib import Path
import csv,hashlib,json,math,re,urllib.request
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/actual_grafana_evidence_20261011'
OUT.mkdir(parents=True,exist_ok=True)
receipts_path=ROOT/'output/requirements_audit_20261009/replay_phone_drain_20261010.json'
latency_path=ROOT/'output/requirements_audit_20261009/grafana_latency_phone_20261010.json'
receipts=json.loads(receipts_path.read_text())
latency=json.loads(latency_path.read_text())
observed={s['id']:s for s in receipts['samples'] if re.fullmatch(r'[a-f0-9]{8}-[a-f0-9]{8}',s.get('id','')) and isinstance(s.get('timestamp'),int) and s['timestamp']>=1704067200}
ids=sorted(observed)
assert len(ids)==657 and latency['measured']==10
source_hash=hashlib.sha256(latency_path.read_bytes()).hexdigest()
token=re.search(r'INFLUX_TOKEN\[\]\s*=\s*"([^"\n]+)"',(ROOT/'include/config.h').read_text(encoding='utf-8'))[1]
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def request(route,body,content='application/json'):
 req=urllib.request.Request('http://127.0.0.1:8181'+route,data=body,headers={'Authorization':'Bearer '+token,'Content-Type':content})
 with opener.open(req,timeout=15) as response: return response.read()
def query(sql):
 return json.loads(request('/api/v3/query_sql',json.dumps({'db':'iot','q':sql,'format':'json'}).encode()))
id_list=','.join("'"+s+"'" for s in ids)
actual_counts=query('SELECT sample_id, COUNT(*) AS rows FROM ku_watch WHERE sample_id IN ('+id_list+') GROUP BY sample_id')
found={r['sample_id']:r['rows'] for r in actual_counts}
assert all(found.get(i)==1 for i in ids), 'Observed set no longer stored exactly once'
lines=[]
for s in latency['samples']:
 assert s['sample_id'] in observed and math.isfinite(s['reference_corrected_delay_ms'])
 r=observed[s['sample_id']]
 fields=','.join(k+'='+str(float(v)) for k,v in {
  'corrected_delay_ms':s['reference_corrected_delay_ms'],
  'mqtt_received_delay_ms':s['mqtt_received_raw_delay_ms'],
  'query_after_mqtt_ms':s['query_after_mqtt_ms'],
  'clock_uncertainty_ms':latency['reference_uncertainty_ms']}.items())
 lines.append('ku_watch_query_measurements,sample_id='+s['sample_id']+',source_hash='+source_hash+' '+fields+' '+str(r['timestamp']))
# These are the ten previously measured results, imported unchanged into a distinct table.
# Capture IDs and timestamps form the point key so repeat imports overwrite the same points.
request('/api/v3/write_lp?db=iot&precision=second',('\n'.join(lines)+'\n').encode(),'text/plain')
measured_where="source_hash='"+source_hash+"'"
check=query('SELECT COUNT(*) AS samples, AVG(corrected_delay_ms) AS mean_ms, MAX(corrected_delay_ms) AS max_ms FROM ku_watch_query_measurements WHERE '+measured_where)[0]
assert check['samples']==10 and abs(check['mean_ms']-latency['corrected_mean_ms'])<.001
ds={'type':'influxdb','uid':'efwpjfdzlacqoc'}
def target(sql):
 return {'datasource':ds,'refId':'A','editorMode':'code','rawQuery':True,'rawSql':sql,'format':'table'}
def panel(i,title,kind,x,y,w,h,sql):
 return {'id':i,'type':kind,'title':title,'gridPos':{'x':x,'y':y,'w':w,'h':h},'datasource':ds,'targets':[target(sql)],
 'fieldConfig':{'defaults':{'mappings':[],'thresholds':{'mode':'absolute','steps':[{'color':'green','value':None}]},'color':{'mode':'fixed','fixedColor':'green'}},'overrides':[]}}
where='sample_id IN (${observed_capture_ids:raw})'
panels=[{'id':1,'type':'text','title':'ขอบเขตผลทดสอบจริง','gridPos':{'x':0,'y':0,'w':24,'h':4},'options':{'mode':'markdown','content':
 '## KU Watch — ผลจากข้อมูลจริงวันที่ 10 ตุลาคม 2569\n'
 '**ชุดรหัสที่รับจริง 657 รหัส** ตรวจฐานข้อมูลซ้ำและแสดงผลผ่าน InfluxDB โดยตรง '
 'ส่วนความหน่วงเป็นผลวัดจริง 10 รหัสจากไฟล์เดิม นำเข้าอีกตารางโดยคงค่าและเวลาเดิม\n\n'
 'ขอบเขตความหน่วงคือ **capture UTC → Grafana query response** ยังไม่รวม browser paint '
 'ความครบ 100% หมายถึงชุดรหัสที่รับและตรวจนี้เท่านั้น ช่วงสลับเครือข่ายเคยเข้าคิวไม่ได้ 26 รายการ'}}]
stats=[
 (2,'รหัสที่รับและอยู่ใน DB','SELECT COUNT(DISTINCT sample_id) AS captures FROM ku_watch WHERE '+where,0,4,6,'none',0),
 (3,'รหัสในชุดที่ไม่พบ','SELECT 657-COUNT(DISTINCT sample_id) AS missing FROM ku_watch WHERE '+where,6,4,6,'none',0),
 (4,'แถวซ้ำของชุดที่ตรวจ','SELECT COUNT(*)-COUNT(DISTINCT sample_id) AS duplicate_rows FROM ku_watch WHERE '+where,12,4,6,'none',0),
 (5,'ชุดที่รับเข้า DB ครบ','SELECT COUNT(DISTINCT sample_id)*100.0/657 AS stored_percent FROM ku_watch WHERE '+where,18,4,6,'percent',1),
 (6,'ความหน่วง query เฉลี่ย','SELECT AVG(corrected_delay_ms) AS mean_ms FROM ku_watch_query_measurements WHERE '+measured_where,0,9,8,'ms',1),
 (7,'ความหน่วง query สูงสุด','SELECT MAX(corrected_delay_ms) AS max_ms FROM ku_watch_query_measurements WHERE '+measured_where,8,9,8,'ms',1),
 (8,'จำนวนรหัสที่วัดความหน่วง','SELECT COUNT(*) AS samples FROM ku_watch_query_measurements WHERE '+measured_where,16,9,8,'none',0),
]
for i,title,sql,x,y,w,unit,decimals in stats:
 p=panel(i,title,'stat',x,y,w,5,sql)
 p['fieldConfig']['defaults'].update({'unit':unit,'decimals':decimals})
 p['options']={'reduceOptions':{'values':False,'calcs':['lastNotNull'],'fields':''},'orientation':'auto','textMode':'auto','colorMode':'value','graphMode':'none'}
 panels.append(p)
p=panel(9,'ความหน่วงแต่ละรหัสที่วัดจริง','barchart',0,14,12,10,
 'SELECT sample_id, corrected_delay_ms FROM ku_watch_query_measurements WHERE '+measured_where+' ORDER BY time')
p['fieldConfig']['defaults'].update({'unit':'ms','min':0})
p['options']={'orientation':'horizontal','xField':'sample_id','showValue':'always','stacking':'none','barWidth':.75,'groupWidth':.7,'legend':{'showLegend':False},'tooltip':{'mode':'single'}}
panels.append(p)
p=panel(10,'รหัสและจำนวนแถวจากฐานข้อมูลจริง','table',12,14,12,10,
 'SELECT sample_id, COUNT(*) AS rows, MIN(time) AS capture_utc FROM ku_watch WHERE '+where+' GROUP BY sample_id ORDER BY sample_id')
p['options']={'showHeader':True,'cellHeight':'sm','footer':{'show':True,'reducer':['count'],'fields':['sample_id']}}
p['fieldConfig']['defaults']['custom']={'filterable':True,'cellOptions':{'type':'auto'}}
panels.append(p)
audit=json.loads((ROOT/'output/soak_audit/status.json').read_text())
panels.append({'id':11,'type':'text','title':'การตรวจระยะยาวยังค้าง','gridPos':{'x':0,'y':24,'w':24,'h':3},'options':{'mode':'markdown','content':
 '### ยังไม่ผ่านการตรวจต่อเนื่อง 24 ชั่วโมง\n'
 'รอบล่าสุดหยุดหลัง **1 ชั่วโมง 30 นาที 24 วินาที** รับสด 5,413 รายการ พบ 2 รอบบูตและช่วงรับห่างสูงสุด 12.097 วินาที '
 'ไม่มีข้อสรุปว่าผ่านครบ 24 ชั่วโมง ผลด้านบนยืนยันเฉพาะข้อมูลที่รับครบชุดและความหน่วง query 10 ตัวอย่าง'}})
dash={'uid':'ku-watch-real-evidence','title':'KU Watch · ผลทดสอบจากข้อมูลจริง','description':'Actual InfluxDB query results for 657 observed IDs and ten saved measured query delays. Does not claim a 24-hour pass.',
 'schemaVersion':39,'version':1,'editable':True,'timezone':'Asia/Bangkok','refresh':'','panels':panels,
 'time':{'from':datetime.fromtimestamp(min(s['timestamp'] for s in observed.values())-60,timezone.utc).isoformat(),'to':datetime.fromtimestamp(max(s['timestamp'] for s in observed.values())+60,timezone.utc).isoformat()},
 'annotations':{'list':[]},'templating':{'list':[{'name':'observed_capture_ids','label':'Observed IDs','type':'constant','hide':2,'query':id_list,'current':{'text':id_list,'value':id_list},'options':[{'text':id_list,'value':id_list,'selected':True}]}]}}
# Existing provider watches this directory; no new server process or authentication change.
destination=ROOT/'integration/grafana/ku-watch-real-evidence.json'
destination.write_text(json.dumps(dash,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'KU_Watch_Actual_Evidence_Import.json').write_text(json.dumps(dash,ensure_ascii=False,indent=2),encoding='utf-8')
with (OUT/'actual_query_measurements.csv').open('w',encoding='utf-8-sig',newline='') as f:
 writer=csv.writer(f);writer.writerow(['sample_id','capture_utc','corrected_delay_ms','clock_uncertainty_ms','source_sha256'])
 for s in latency['samples']:writer.writerow([s['sample_id'],datetime.fromtimestamp(observed[s['sample_id']]['timestamp'],timezone.utc).isoformat(),s['reference_corrected_delay_ms'],latency['reference_uncertainty_ms'],source_hash])
report={'data_type':'ACTUAL','prepared_utc':datetime.now(timezone.utc).isoformat(),'observed_ids':len(ids),'stored_once':sum(found.get(i)==1 for i in ids),'query_measurements':check,'source_latency_sha256':source_hash,'source_receipts_sha256':hashlib.sha256(receipts_path.read_bytes()).hexdigest(),'actual_24h_audit_status':audit['status'],'dashboard_uid':dash['uid'],'panels':len(panels),'no_new_grafana_server':True,'hardware_24h_pass_claim':False}
(OUT/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
