"""Discover the authenticated watch on the current hotspot; no credential output."""
from pathlib import Path
import argparse,base64,concurrent.futures,json,re,subprocess,urllib.request
ROOT=Path(__file__).resolve().parents[1]
file=ROOT/'config/watch-access.local.json';saved=json.loads(file.read_text())
version=re.search(r'VERSION="([\d.]+)"',(ROOT/'include/watch_extensions.h').read_text())[1]
auth='Basic '+base64.b64encode((saved['username']+':'+saved['password']).encode()).decode()
parser=argparse.ArgumentParser();parser.add_argument('--windows-hotspot',action='store_true');parser.add_argument('--output',default='output/requirements_audit_20261009/clock_network_20261010.json');args=parser.parse_args()
if args.windows_hotspot:
    result=subprocess.run(['powershell','-NoProfile','-Command',"Get-NetNeighbor -AddressFamily IPv4 | Where-Object { $_.IPAddress -like '192.168.137.*' -and $_.LinkLayerAddress -eq 'D4-05-92-44-51-AC' } | Select-Object -ExpandProperty IPAddress"],capture_output=True,text=True,check=True)
    hosts=[s.strip() for s in result.stdout.splitlines() if s.strip().startswith('192.168.137.')]
    if not hosts:raise SystemExit('Watch DHCP neighbor not found on Windows hotspot')
else:hosts=['172.20.10.'+str(host) for host in range(2,15)]
def check(host):
    url='http://'+host
    try:
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(urllib.request.Request(url+'/status',headers={'Authorization':auth}),timeout=2) as response:status=json.load(response)
        if status.get('firmware')==version:return url,status
    except (OSError,ValueError):pass
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:results=[r for r in pool.map(check,hosts) if r]
if len(results)!=1:print('Watch online matches:',len(results));raise SystemExit(1)
url,status=results[0];saved['url']=url;file.write_text(json.dumps(saved,indent=2))
(ROOT/args.output).write_text(json.dumps(status,indent=2))
print(json.dumps({k:status[k] for k in ['firmware','wifi','mqtt','uptime','unix','queue_pending','queue_dropped'] if k in status}))
