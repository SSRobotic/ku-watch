"""Read actual backend availability and latest trusted capture counts, no raw GPS/pulse."""
from pathlib import Path
import json,re,urllib.request
ROOT=Path(__file__).resolve().parents[1]
token=re.search(r'INFLUX_TOKEN\[\]\s*=\s*"([^"\n]+)"',(ROOT/'include/config.h').read_text(encoding='utf8'))[1]
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
result={}
for name,url in [('node_red','http://127.0.0.1:1880/'),('grafana','http://127.0.0.1:3000/api/health')]:
    try:
        with opener.open(url,timeout=3) as response:result[name]={'http':response.status}
    except OSError:result[name]={'available':False}
try:
    sql="SELECT COUNT(*) AS rows, COUNT(DISTINCT sample_id) AS captures, MAX(time) AS latest FROM ku_watch WHERE time > now() - INTERVAL '5 minutes'"
    req=urllib.request.Request('http://127.0.0.1:8181/api/v3/query_sql',data=json.dumps({'db':'iot','q':sql,'format':'json'}).encode(),headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
    with opener.open(req,timeout=5) as response:result['database']=json.load(response)
except OSError:result['database']={'available':False}
(ROOT/'output/requirements_audit_20261009/backend_20261010.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
