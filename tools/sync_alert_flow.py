"""Add the watch alert card; preserve existing flows and private credentials."""
import json
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import URLError
ROOT=Path(__file__).resolve().parents[1]
def update(nodes):
    from sync_network_flow import update as network_update
    network_update(nodes)
    route=next(n for n in nodes if n['id']=='ku_cloud_replay_route')
    node=next((n for n in nodes if n['id']=='ku_cloud_alert_card'),None)
    if node is None:
        node={'id':'ku_cloud_alert_card','type':'ui-template','z':route['z'],'group':'ku_cloud_alert_group',
              'name':'Environment alerts','order':1,'width':0,'height':0,'storeOutMessages':False,
              'passthru':False,'resendOnRefresh':True,'templateScope':'local','x':920,'y':960,'wires':[[]]}
        nodes.append(node)
        nodes.append({'id':'ku_cloud_alert_group','type':'ui-group','name':'แจ้งเตือนสิ่งแวดล้อม','page':'a47ef3e6e3d00b0d',
                      'width':'12','height':'4','order':8,'showTitle':True,'className':'','visible':'true','disabled':'false','groupType':'default'})
    node['format']=(ROOT/'integration/node-red/environment_alert.vue').read_text(encoding='utf-8')
    if node['id'] not in route['wires'][1]:route['wires'][1].append(node['id'])
def save(path,nodes):path.write_text(json.dumps(nodes,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
    backup=ROOT/'output/alert_backup_20261008';backup.mkdir(exist_ok=True)
    portable=ROOT/'integration/node-red/ku-watch-cloud-flow.json'
    nodes=json.loads(portable.read_text(encoding='utf-8-sig'))
    if not (backup/'portable-flow.json').exists():save(backup/'portable-flow.json',nodes)
    update(nodes);save(portable,nodes)
    try:
        with urlopen(Request('http://127.0.0.1:1880/flows',headers={'Node-RED-API-Version':'v2'}),timeout=3) as r:runtime=json.load(r)
    except URLError:runtime=None
    if runtime:
        if not (backup/'runtime-flow.json').exists():save(backup/'runtime-flow.json',runtime['flows'])
        update(runtime['flows'])
        req=Request('http://127.0.0.1:1880/flows',data=json.dumps(runtime).encode(),method='POST',headers={
            'Content-Type':'application/json','Node-RED-API-Version':'v2','Node-RED-Deployment-Type':'nodes'})
        with urlopen(req,timeout=10) as r:r.read()
        print('Environmental alert card deployed to Node-RED live view.')
    else:
        path=Path.home()/'.node-red/flows.json';nodes=json.loads(path.read_text(encoding='utf-8-sig'))
        if not (backup/'local-flow.json').exists():save(backup/'local-flow.json',nodes)
        update(nodes);save(path,nodes);print('Environmental alert card saved for next Node-RED start.')
if __name__=='__main__':main()
