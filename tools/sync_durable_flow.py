"""Install a local durable DB spool without exposing or changing credentials."""
import json
from pathlib import Path
from urllib.request import Request,urlopen
ROOT=Path(__file__).resolve().parents[1]
def update(nodes):
    formatter=next(n for n in nodes if n['id']=='ku_cloud_influx_format')
    formatter['func']=(ROOT/'integration/node-red/to_influx.js').read_text(encoding='utf-8')
    broker=next(n for n in nodes if n['id']=='ku_cloud_broker');broker['cleansession']=False
    status=next(n for n in nodes if n['id']=='ku_cloud_write_status')
    status['func']="const ok=msg.statusCode===202; node.status({fill:ok?'green':'red',shape:ok?'dot':'ring',text:ok?'Saved to durable DB queue':'DB queue unavailable'}); return null;"
    status['name']='Durable DB queue receipt'
def main():
    backup=ROOT/'output/small_finish_backup_20261008'
    portable=ROOT/'integration/node-red/ku-watch-cloud-flow.json'
    nodes=json.loads(portable.read_text(encoding='utf-8-sig'));update(nodes)
    portable.write_text(json.dumps(nodes,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with urlopen(Request('http://127.0.0.1:1880/flows',headers={'Node-RED-API-Version':'v2'}),timeout=3) as r:runtime=json.load(r)
    (backup/'flow_before_durable.json').write_text(json.dumps(runtime['flows'],ensure_ascii=False),encoding='utf-8')
    update(runtime['flows'])
    req=Request('http://127.0.0.1:1880/flows',data=json.dumps(runtime).encode(),method='POST',headers={
        'Content-Type':'application/json','Node-RED-API-Version':'v2','Node-RED-Deployment-Type':'nodes'})
    with urlopen(req,timeout=10) as r:r.read()
    print('Durable DB spool route deployed; private credentials preserved.')
if __name__=='__main__':main()
