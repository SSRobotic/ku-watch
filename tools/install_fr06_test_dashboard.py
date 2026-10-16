"""Add an isolated, clearly labelled test-input page; leave live-data routes intact."""
from pathlib import Path
from datetime import datetime,timezone
import json,urllib.request
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/fr_completion_20261016'
headers={'Node-RED-API-Version':'v2'}
with urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:1880/flows',headers=headers),timeout=5) as response:runtime=json.load(response)
backup=OUT/'flows_before_fr06.private.json'
if not backup.exists():backup.write_text(json.dumps(runtime,ensure_ascii=False,indent=2),'utf8')
nodes=runtime['flows'];existing={n['id']:n for n in nodes}
original_input=existing['ku_cloud_input'];page=existing['a47ef3e6e3d00b0d']
topic=json.loads((ROOT/'config/cloud.local.json').read_text())['topic'] if 'topic' in json.loads((ROOT/'config/cloud.local.json').read_text()) else None
if not topic:
    import re
    topic=original_input['topic']
assert '+' not in topic and '#' not in topic
template=(ROOT/'integration/node-red/environment_alert.vue').read_text('utf8')
template=template.replace('<div class="ku-alerts">','<div class="ku-alerts" :data-test-id="p.test_id" :data-sequence="p.sequence">\n    <h2 style="color:#a16207">FR-06 TEST — ค่าจำลองเพื่อทดสอบระบบ</h2>\n    <p>ป้อนค่าใหม่ 1 Hz จากนาฬิกาจริง · แยกจากข้อมูลเซ็นเซอร์จริงและฐานข้อมูล</p>')
changes=[
 {**page,'id':'ku_fr06_test_page','name':'FR-06 Test','path':'/fr06-test','order':20},
 {'id':'ku_fr06_test_group','type':'ui-group','name':'Hardware acceptance — simulated inputs','page':'ku_fr06_test_page','width':'12','height':'8','order':1,'showTitle':True,'className':'','visible':'true','disabled':'false','groupType':'default'},
 {**original_input,'id':'ku_fr06_test_mqtt','name':'Explicit device alert fixtures only','topic':topic+'/test/alerts','qos':'1','datatype':'json','x':210,'y':1220,'wires':[['ku_fr06_test_filter']]},
 {'id':'ku_fr06_test_filter','type':'function','z':original_input['z'],'name':'Require explicit simulated device event','func':'const p=msg.payload; if(!p || p.kind!=="alert_fixture" || p.simulated!==true || !Number.isInteger(p.test_id) || ![1,2,3].includes(p.sequence)) return null; return msg;','outputs':1,'timeout':0,'noerr':0,'initialize':'','finalize':'','libs':[],'x':530,'y':1220,'wires':[['ku_fr06_test_card']]},
 {'id':'ku_fr06_test_card','type':'ui-template','z':original_input['z'],'group':'ku_fr06_test_group','name':'FR-06 explicit test inputs','order':1,'width':0,'height':0,'storeOutMessages':False,'passthru':False,'resendOnRefresh':True,'templateScope':'local','x':850,'y':1220,'format':template,'wires':[[]]}
]
for change in changes:
    if change['id'] in existing:nodes[nodes.index(existing[change['id']])]=change
    else:nodes.append(change)
request=urllib.request.Request('http://127.0.0.1:1880/flows',data=json.dumps(runtime).encode(),method='POST',headers={**headers,'Content-Type':'application/json','Node-RED-Deployment-Type':'nodes'})
with urllib.request.urlopen(request,timeout=15) as response:response.read()
result={'installed_utc':datetime.now(timezone.utc).isoformat(),'page':'http://127.0.0.1:1880/dashboard/fr06-test','source':'Device-published, explicitly simulated inputs','influx_routes_added':0,'production_sensor_routes_changed':False,'new_node_ids':[n['id'] for n in changes]}
(OUT/'fr06_dashboard_install.json').write_text(json.dumps(result,indent=2),'utf8');print(json.dumps(result))
