"""Real device endpoint failure for ten minutes, with Wi-Fi still connected.
Changes only the MQTT port, preserves credentials and restores it in finally.
This does not stop the shared HiveMQ service or claim it was stopped.
"""
from pathlib import Path
import argparse,base64,html,json,re,subprocess,time,urllib.request,urllib.parse
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/requirements_audit_20261009'
PYTHON=Path.home()/'.platformio/penv/Scripts/python.exe'

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--seconds',type=int,default=600);args=parser.parse_args()
    if not 10<=args.seconds<=600:parser.error('10..600 seconds required')
    saved=json.loads((ROOT/'config/watch-access.local.json').read_text())
    url=saved['url'].rstrip('/')+'/'
    authorization='Basic '+base64.b64encode((saved['username']+':'+saved['password']).encode()).decode()
    def request(route,data=None):
        with urllib.request.urlopen(urllib.request.Request(url+route,data=data,headers={'Authorization':authorization}),timeout=8) as r:return r.read()
    def reopen():
        subprocess.run([str(PYTHON),str(ROOT/'tools/hub_console.py'),'--seconds','2','--command','LINKCMD 13','--output',str(OUT/'broker_setup.json')],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=8,check=True)
    def read(route):
        try:return request(route)
        except OSError:reopen();return request(route)
    def fields():return {k:html.unescape(v) for k,v in re.findall(r"name='([^']+)'[^>]*value=\"([^\"]*)\"",read('').decode())}
    def set_port(port):
        form=fields();form['port']=str(port);form['token']=saved['password'];request('save',urllib.parse.urlencode(form).encode())
    def status():return json.loads(read('status'))
    restoration=ROOT/'config/broker-outage-restore.local.json'
    report={'boundary':'Actual watch connects to closed MQTT port 1; Wi-Fi stays available; does not stop shared broker','requested_seconds':args.seconds,'states':[],'restored':False}
    original=int(fields()['port']);restoration.write_text(json.dumps({'original_port':original}))
    observer=subprocess.Popen(['C:/Program Files/nodejs/node.exe',str(ROOT/'tools/observe_replay.cjs'),str(OUT/'broker_replay.json'),'1800000'],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
    changed=False
    try:
        time.sleep(3);report['before']=status()
        if report['before']['recording'] or not report['before']['wifi'] or not report['before']['mqtt']:raise RuntimeError('Watch must be idle and online')
        set_port(1);changed=True
        deadline=time.monotonic()+30
        while time.monotonic()<deadline:
            current=status()
            if current['wifi'] and not current['mqtt']:break
            time.sleep(1)
        else:raise RuntimeError('Did not establish MQTT-only failure')
        started=time.monotonic();report['started_utc']=time.time()
        # Reset the setup portal's ten-minute timer once mid-test. This does not
        # change the station connection, MQTT endpoint or saved settings.
        renewed=False
        while time.monotonic()-started<args.seconds:
            current=status();report['states'].append({'at_s':round(time.monotonic()-started,2),**current})
            (OUT/'broker_outage_progress.json').write_text(json.dumps(report,indent=2))
            if not current['wifi'] or current['mqtt']:raise RuntimeError('Fault window did not preserve Wi-Fi/MQTT-only failure')
            if current['dropped']!=report['before']['dropped'] or current['storage_errors']!=report['before']['storage_errors']:raise RuntimeError('Watch storage lost data')
            if args.seconds>=400 and not renewed and time.monotonic()-started>=350:
                request('close',urllib.parse.urlencode({'token':saved['password']}).encode());time.sleep(.5);reopen();renewed=True
            print('MQTT failure seconds',round(time.monotonic()-started),'pending',current['pending'],flush=True)
            time.sleep(min(15,max(0,args.seconds-(time.monotonic()-started))))
        report['observed_seconds']=time.monotonic()-started
    except Exception as error:report['error']=type(error).__name__
    finally:
        if changed:
            try:
                set_port(original);report['restored']=True;restoration.unlink(missing_ok=True)
            except Exception as error:report['restore_error']=type(error).__name__
        else:restoration.unlink(missing_ok=True)
    if report['restored']:
        deadline=time.monotonic()+600
        while time.monotonic()<deadline:
            current=status()
            if current['wifi'] and current['mqtt'] and current['pending']<=2:break
            time.sleep(2)
        report['after']=current
    observer.terminate();observer.wait(timeout=5)
    if (OUT/'broker_replay.json').exists():
        samples=json.loads((OUT/'broker_replay.json').read_text())['samples']
        unique={p['id']:p for p in samples if p.get('id')}
        history=[p for p in unique.values() if p.get('backfill')]
        report['received_unique']=len(unique);report['backfill_unique']=len(history)
        report['backfill_trusted_time']=all(isinstance(p.get('timestamp'),int) and p['timestamp']>=1704067200 for p in history)
        grouped={}
        for packet in unique.values():
            session,sequence=packet['id'].split('-');grouped.setdefault(session,set()).add(int(sequence,16))
        report['sessions_observed']=len(grouped)
        report['missing_sequences']=sum(max(ids)-min(ids)+1-len(ids) for ids in grouped.values() if ids)
        # Confirm replay reached the database, not just the MQTT subscriber.
        token=re.search(r'INFLUX_TOKEN\[\]\s*=\s*"([^"\n]+)"',(ROOT/'include/config.h').read_text(encoding='utf8'))[1]
        ids=[p['id'].lower() for p in history if re.fullmatch(r'[a-fA-F0-9]{8}-[a-fA-F0-9]{8}',p['id'])]
        report['database_rows']=0;report['database_distinct_captures']=0
        for offset in range(0,len(ids),200):
            group=ids[offset:offset+200]
            sql="SELECT COUNT(*) AS rows, COUNT(DISTINCT sample_id) AS captures FROM ku_watch WHERE sample_id IN ("+','.join("'"+key+"'" for key in group)+")"
            for attempt in range(30):
                req=urllib.request.Request('http://127.0.0.1:8181/api/v3/query_sql',data=json.dumps({'db':'iot','q':sql,'format':'json'}).encode(),headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
                with urllib.request.urlopen(req,timeout=8) as response:counts=json.load(response)[0]
                if counts['captures']==len(group):break
                time.sleep(1)
            report['database_rows']+=counts['rows'];report['database_distinct_captures']+=counts['captures']
        report['database_complete']=report['database_rows']==report['database_distinct_captures']==len(history)
    report['passed']=not report.get('error') and report['restored'] and report.get('observed_seconds',0)>=args.seconds and report.get('after',{}).get('pending',999)<=2 and report.get('backfill_unique',0)>=args.seconds-3 and report.get('backfill_trusted_time') and report.get('missing_sequences')==0 and report.get('database_complete')
    (OUT/'broker_outage.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='states'}))
    return 0 if report['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
