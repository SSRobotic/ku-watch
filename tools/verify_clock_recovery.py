"""Verify actual NTP recovery and elapsed time without setting either clock."""
from pathlib import Path
import base64,json,time,urllib.request
ROOT=Path(__file__).resolve().parents[1]
saved=json.loads((ROOT/'config/watch-access.local.json').read_text())
auth='Basic '+base64.b64encode((saved['username']+':'+saved['password']).encode()).decode()
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def status():
    with opener.open(urllib.request.Request(saved['url'].rstrip('/')+'/status',headers={'Authorization':auth}),timeout=5) as response:return json.load(response)
before=status();started=time.monotonic();time.sleep(8);after=status();elapsed=time.monotonic()-started
report={'boundary':'Read-only authenticated status; no manual/USB clock set. Windows outgoing hotspot is 2.4GHz; incoming PC Wi-Fi is a separate interface connection.','before':before,'after':after,'elapsed_s':elapsed,'utc_advance':after['utc']-before['utc'],'host_utc_delta_s':abs(after['utc']-time.time())}
report['passed']=before['clock_source']==after['clock_source']=='NET TIME' and after['wifi'] and abs(report['utc_advance']-elapsed)<2 and report['host_utc_delta_s']<5 and after['uptime_ms']>before['uptime_ms']
(ROOT/'output/requirements_audit_20261009/clock_recovery_20261010.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report));raise SystemExit(0 if report['passed'] else 1)
