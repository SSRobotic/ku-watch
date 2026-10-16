"""USB diagnostics with explicit safe output allowlist; credentials stay private."""
import argparse,json,re,time
from pathlib import Path
from activity_export import Watch
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--refresh-access',action='store_true');a=p.parse_args()
target=ROOT/a.output;target.parent.mkdir(parents=True,exist_ok=True)
if target.exists():raise FileExistsError('Keep previous evidence')
w=Watch('COM15');report={'checked_utc':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),'commands':{},'credential_values_logged':False}
try:
 report['activity_status']=w.status()
 for command in ['SETTINGSINFO','NETINFO','CLOCKINFO','OTAINFO','SCREENINFO','ALERTINFO','POWERINFO']+(['SETUPAUTH'] if a.refresh_access else []):
  w.send(command);lines=[];end=time.monotonic()+.7
  while time.monotonic()<end:
   line=w.serial.readline().decode('ascii','replace').strip()
   if command=='SETUPAUTH' and line.startswith('SETUPAUTH '):
    parts=line.split()
    if len(parts)==3 and re.fullmatch(r'[0-9.]+',parts[1]) and parts[1]!='0.0.0.0':
     config=ROOT/'config/watch-access.local.json';prior=json.loads(config.read_text()) if config.exists() else {}
     prior.update(url='http://'+parts[1],username='admin',password=parts[2]);config.write_text(json.dumps(prior),encoding='utf8');report['access_refreshed']=True
   elif line.startswith(('SETTINGS ','NETWORK ','QUEUE ','CLOCK ','OTA ','SCREEN ','LCD ','ALERT ','POWER ')):lines.append(line)
  if command!='SETUPAUTH':report['commands'][command]=lines
finally:w.close()
target.write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report))
