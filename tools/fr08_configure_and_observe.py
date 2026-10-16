"""Configure the real release URL and observe automatic update; never send OTACHECK."""
from pathlib import Path
from datetime import datetime,timezone
import json,time,argparse
from fr_device_session import open_portal,close_portal,fields,request,usb
from activity_export import Watch
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/fr_completion_20261016'
p=argparse.ArgumentParser();p.add_argument('--target',default='2.0.11');p.add_argument('--attempt',default='');a=p.parse_args()
if a.attempt and not a.attempt.replace('_','').isalnum():raise ValueError('Portable attempt name required')
target=OUT/('fr08_auto_update_'+a.target+('_'+a.attempt if a.attempt else '')+'.json')
if target.exists():raise FileExistsError('Preserve earlier OTA observation')
c=json.loads((ROOT/'config/ota-fr08.local.json').read_text());url='https://'+c['host']+':'+str(c['port'])+'/r/'+c['capability']+'/manifest.json'
report={'started_utc':datetime.now(timezone.utc).isoformat(),'manual_otacheck_sent':False,'firmware_uploaded_over_usb_in_this_test':False,'lines':[]}
before=open_portal();form=fields();form['manifest']=url
request('save',form);close_portal();report['from_version']=before['firmware'];report['manifest_configured']=True
watch=Watch('COM15');start=time.monotonic();last_query=0;confirmed_at=None
try:
    while time.monotonic()-start<160:
        elapsed=time.monotonic()-start
        if elapsed-last_query>5:
            watch.send('OTAINFO');last_query=elapsed
        line=watch.serial.readline().decode('ascii','replace').strip()
        if line.startswith(('OTA ','SETTINGS ','ESP-ROM','rst:','Guru Meditation','Backtrace','Rebooting','abort')):
            report['lines'].append({'elapsed_ms':round(elapsed*1000,2),'received_utc':datetime.now(timezone.utc).isoformat(),'text':line})
            if line.startswith('OTA '):print(line,flush=True)
            if confirmed_at is None and line.startswith('OTA version='+a.target+' ') and 'confirmed=1' in line:
                confirmed_at=elapsed
        if confirmed_at and elapsed-confirmed_at>=6:break
except Exception as error:
    report['serial_observation_error']=type(error).__name__
finally:watch.close()
report['completed_utc']=datetime.now(timezone.utc).isoformat()
report['download_verified']=any('OTA VERIFIED version='+a.target+' ' in x['text'] for x in report['lines'])
report['new_version_boot_confirmed']=confirmed_at is not None
report['target_version']=a.target
report['passed']=report['from_version']!=a.target and report['download_verified'] and report['new_version_boot_confirmed']
target.write_text(json.dumps(report,indent=2),'utf8');print(json.dumps({k:v for k,v in report.items() if k!='lines'}))
