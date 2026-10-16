"""Close the authenticated setup portal without exposing its credentials."""
import argparse,base64,json,re,urllib.parse,urllib.request
from pathlib import Path
root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--output',default='output/requirements_audit_20261009/close_setup_final.json');args=parser.parse_args()
saved=json.loads((root/'config/watch-access.local.json').read_text())
auth='Basic '+base64.b64encode((saved['username']+':'+saved['password']).encode()).decode()
request=urllib.request.Request(saved['url'].rstrip('/')+'/close',data=urllib.parse.urlencode({'token':saved['password']}).encode(),headers={'Authorization':auth})
with urllib.request.urlopen(request,timeout=8) as response:status=response.status
print('Setup close HTTP',status)
version=re.search(r'VERSION="([\d.]+)"',(root/'include/watch_extensions.h').read_text())[1]
(root/args.output).write_text(json.dumps({'status':status,'version':version}))
