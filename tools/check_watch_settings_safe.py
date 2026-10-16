"""Verify saved network identity without displaying passwords or capability URLs."""
from pathlib import Path
import argparse,base64,html,json,re,urllib.request
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--output',default='output/requirements_audit_20261009/network_settings_20261010.json');args=parser.parse_args()
s=json.loads((ROOT/'config/watch-access.local.json').read_text())
auth='Basic '+base64.b64encode((s['username']+':'+s['password']).encode()).decode()
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with opener.open(urllib.request.Request(s['url'].rstrip('/')+'/',headers={'Authorization':auth}),timeout=5) as r:page=r.read().decode()
fields={k:html.unescape(v) for k,v in re.findall(r"name='([^']+)'[^>]*value=\"([^\"]*)\"",page)}
result={k:fields[k] for k in ['port','tls','topic','logging','shunt']}
cloud=json.loads((ROOT/'config/cloud.local.json').read_text())
expected=json.loads((ROOT/'config/wifi-replacement.local.json').read_text())
result.update(ssid_expected=fields['ssid']==expected['ssid'],host_expected=fields['host']==cloud['host'],user_expected=fields['user']==cloud['watch_user'])
print(json.dumps(result));(ROOT/args.output).write_text(json.dumps(result,indent=2))
