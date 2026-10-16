"""Update only the KU Watch formatter; leave other flows and credentials intact."""
import json
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError

ROOT=Path(__file__).resolve().parents[1]
SOURCE=(ROOT/'integration/node-red/to_influx.js').read_text(encoding='utf-8')
NODE='ku_cloud_influx_format'

def replace(nodes):
    matches=[n for n in nodes if n.get('id')==NODE]
    if len(matches)!=1:
        raise RuntimeError('Expected exactly one KU Watch formatter; no changes made')
    changed=matches[0].get('func')!=SOURCE
    matches[0]['func']=SOURCE
    return changed

def save(path, nodes):
    path.write_text(json.dumps(nodes,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

portable=ROOT/'integration/node-red/ku-watch-cloud-flow.json'
nodes=json.loads(portable.read_text(encoding='utf-8-sig'))
if replace(nodes): save(portable,nodes)

# Read live revision when the runtime is available. Do not overwrite newer edits.
try:
    req=Request('http://127.0.0.1:1880/flows',headers={'Node-RED-API-Version':'v2'})
    with urlopen(req,timeout=3) as response: runtime=json.load(response)
except URLError:
    runtime=None
if runtime is not None:
    if replace(runtime['flows']):
        req=Request('http://127.0.0.1:1880/flows',data=json.dumps(runtime).encode(),method='POST',
                    headers={'Content-Type':'application/json','Node-RED-API-Version':'v2',
                             'Node-RED-Deployment-Type':'nodes'})
        with urlopen(req,timeout=10) as response: response.read()
    print('KU Watch formatter deployed to running Node-RED.')
else:
    local=Path.home()/'.node-red/flows.json'
    nodes=json.loads(local.read_text(encoding='utf-8-sig'))
    original=next(n['func'] for n in nodes if n.get('id')==NODE)
    if replace(nodes):
        backup=ROOT/'output/backup_before_spo2_iaq_20261002/node-red-local-formatter.js'
        if not backup.exists(): backup.write_text(original,encoding='utf-8')
        save(local,nodes)
    print('Node-RED is stopped. Saved updated formatter for its next start.')
