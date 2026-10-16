"""Read-only check of loaded dashboards and health; does not measure DOM paint."""
from pathlib import Path
import json,sqlite3,urllib.request,urllib.error
ROOT=Path(__file__).resolve().parents[1]
report={'boundary':'Stored Grafana dashboards and health only; no browser paint claim','dashboards':{}}
con=sqlite3.connect('file:D:/iot2026/Grafana/grafana/data/grafana.db?mode=ro',uri=True)
try:
    for uid in ['ku-watch-live','ku-watch-friends']:
        row=con.execute('SELECT data FROM dashboard WHERE uid=?',(uid,)).fetchone()
        data=json.loads(row[0]) if row else None
        if data is None:
            row=con.execute("SELECT value FROM resource WHERE resource='dashboards' AND name=?",(uid,)).fetchone()
            if row:data=json.loads(row[0])['spec']
        report['dashboards'][uid]={'found':data is not None,'refresh':data.get('refresh') if data else None}
finally:con.close()
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
for name,route in [('health','/api/health'),('frontend','/api/frontend/settings')]:
    try:
        with opener.open('http://127.0.0.1:3000'+route,timeout=8) as response: data=json.load(response)
        report[name]={'database':data.get('database')} if name=='health' else {'min_refresh_interval':data.get('minRefreshInterval')}
    except urllib.error.HTTPError as e:report[name]={'http_status':e.code}
    except (OSError,ValueError):report[name]={'unavailable':True}
report['live_refresh_loaded']=report['dashboards']['ku-watch-live']['refresh']=='1s'
target=ROOT/'output/requirements_audit_20261009/grafana_runtime_20261010.json'
target.write_text(json.dumps(report,indent=2));print(json.dumps(report))
