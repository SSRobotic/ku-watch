"""Observe queue recovery read-only; never discard saved captures or reset firmware."""
from pathlib import Path
import base64,json,time,urllib.request
ROOT=Path(__file__).resolve().parents[1];out=ROOT/'output/requirements_audit_20261009'
saved=json.loads((ROOT/'config/watch-access.local.json').read_text())
auth='Basic '+base64.b64encode((saved['username']+':'+saved['password']).encode()).decode()
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
report={'boundary':'Actual queue after restart and Wi-Fi replacement; no synthetic outage and no queue deletion','states':[],'passed':False};start=time.monotonic()
for attempt in range(40):
    try:
        with opener.open(urllib.request.Request(saved['url'].rstrip('/')+'/status',headers={'Authorization':auth}),timeout=5) as response:state=json.load(response)
    except OSError:
        report['error']='Status unavailable';break
    report['states'].append({'at_s':round(time.monotonic()-start,2),**state})
    print(json.dumps({'at_s':round(time.monotonic()-start),'pending':state['pending'],'dropped':state['dropped'],'wifi':state['wifi'],'mqtt':state['mqtt']}),flush=True)
    if state['wifi'] and state['mqtt'] and state['pending']<=2:
        report['passed']=True;break
    if len(report['states'])>1 and state['uptime_ms']<report['states'][-2]['uptime_ms']:
        report['error']='Watch restarted during queue audit';break
    (out/'queue_recovery_20261010.json').write_text(json.dumps(report,indent=2));time.sleep(10)
report['elapsed_s']=round(time.monotonic()-start,2)
report['dropped_change']=report['states'][-1]['dropped']-report['states'][0]['dropped'] if report['states'] else None
(out/'queue_recovery_20261010.json').write_text(json.dumps(report,indent=2));print('Queue recovery passed:',report['passed'])
raise SystemExit(0 if report['passed'] else 1)
