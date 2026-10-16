"""Let the existing real temperature chart scale to received values; no value edits."""
from pathlib import Path
from datetime import datetime,timezone
import json,urllib.request
ROOT=Path(__file__).resolve().parents[1];target=ROOT/'output/final_acceptance_20261016/dashboard_scale.json'
if target.exists():raise FileExistsError('Keep earlier evidence')
req=urllib.request.Request('http://127.0.0.1:1880/flows',headers={'Node-RED-API-Version':'v2'})
with urllib.request.urlopen(req,timeout=10) as r:state=json.load(r)
nodes=[n for n in state['flows'] if n.get('id')=='b3abffd17f020a7d' and n.get('type')=='ui-chart'];assert len(nodes)==1
chart=nodes[0];before={k:chart[k] for k in ['id','name','ymin','ymax']};chart.update(ymin='',ymax='')
request=urllib.request.Request('http://127.0.0.1:1880/flows',method='POST',data=json.dumps(state).encode(),headers={'Content-Type':'application/json','Node-RED-API-Version':'v2','Node-RED-Deployment-Type':'nodes'})
with urllib.request.urlopen(request,timeout=15) as r:r.read()
with urllib.request.urlopen(req,timeout=10) as r:after=json.load(r)
readback=next(n for n in after['flows'] if n.get('id')==chart['id']);assert readback['ymin']==readback['ymax']==''
report={'updated_utc':datetime.now(timezone.utc).isoformat(),'before':before,'after':{k:readback[k] for k in ['id','name','ymin','ymax']},'boundary':'Only chart axis bounds changed to automatic; actual sensor values, routes and database points unchanged. Board temperature is not calibrated ambient temperature.','passed':True}
target.write_text(json.dumps(report,indent=2),encoding='utf8');(ROOT/'integration/node-red/temperature-chart-scale.json').write_text(json.dumps(report['after'],indent=2),encoding='utf8');print(json.dumps(report))
