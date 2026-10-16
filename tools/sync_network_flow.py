"""Deploy only the existing watch MQTT input, replay routing and formatter."""
import json
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import URLError
ROOT=Path(__file__).resolve().parents[1]
FORMAT=(ROOT/'integration/node-red/to_influx.js').read_text(encoding='utf-8')
ROUTE=(ROOT/'integration/node-red/route_telemetry.js').read_text(encoding='utf-8')
def update(nodes):
    source=next(n for n in nodes if n['id']=='ku_cloud_input')
    formatter=next(n for n in nodes if n['id']=='ku_cloud_influx_format')
    source['qos']='1';formatter['func']=FORMAT
    route=next((n for n in nodes if n['id']=='ku_cloud_replay_route'),None)
    if route is None:
        live=[target for target in source['wires'][0] if target!='ku_cloud_influx_format']
        route={'id':'ku_cloud_replay_route','type':'function','z':source['z'],'name':'Capture history / live view',
               'func':ROUTE,'outputs':2,'x':560,'y':650,'wires':[['ku_cloud_influx_format'],live]}
        nodes.append(route)
    else:route['func']=ROUTE
    source['wires']=[['ku_cloud_replay_route']]
def save(path,nodes):path.write_text(json.dumps(nodes,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
    portable=ROOT/'integration/node-red/ku-watch-cloud-flow.json'
    nodes=json.loads(portable.read_text(encoding='utf-8-sig'));update(nodes);save(portable,nodes)
    try:
        with urlopen(Request('http://127.0.0.1:1880/flows',headers={'Node-RED-API-Version':'v2'}),timeout=3) as r:runtime=json.load(r)
    except URLError:runtime=None
    if runtime is not None:
        backup=ROOT/'output/network_backup_20261008/node-red-runtime.json'
        if not backup.exists():save(backup,runtime['flows'])
        update(runtime['flows'])
        req=Request('http://127.0.0.1:1880/flows',data=json.dumps(runtime).encode(),method='POST',
                    headers={'Content-Type':'application/json','Node-RED-API-Version':'v2','Node-RED-Deployment-Type':'nodes'})
        with urlopen(req,timeout=10) as r:r.read()
        print('Watch replay route and QoS1 deployed; other nodes preserved.')
    else:
        local=Path.home()/'.node-red/flows.json';nodes=json.loads(local.read_text(encoding='utf-8-sig'))
        backup=ROOT/'output/network_backup_20261008/node-red-local.json'
        if not backup.exists():save(backup,nodes)
        update(nodes);save(local,nodes);print('Saved watch replay route for next Node-RED start.')

if __name__=='__main__':main()
