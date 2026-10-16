"""Observe current device display/quality counters; never collect raw PPG or GPS."""
import json,re,threading,time
from datetime import datetime,timezone
from pathlib import Path
from activity_export import Watch
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/fr_completion_20261016/sensor_display_finger_65s.json'
if OUT.exists():raise FileExistsError('Preserve previous observation')
report={'started_utc':datetime.now(timezone.utc).isoformat(),'boundary':'Actual USB responses after display writes, not a camera proof or calibration. No raw optical or location samples.','watch':[],'hub':[],'errors':[]}
def observe(port,key,commands):
 w=Watch(port);start=time.monotonic();due=0
 try:
  while time.monotonic()-start<65:
   elapsed=time.monotonic()-start
   if elapsed>=due:
    for command in commands:w.send(command)
    due+=1
   line=w.serial.readline().decode('ascii','replace').strip()
   if line.startswith(('SENSORS ','SCREEN ','HUBINFO ','HUB CLOCK ','HUB PERFORMANCE ')):
    report[key].append({'received_utc':datetime.now(timezone.utc).isoformat(),'elapsed_ms':round(elapsed*1000,2),'text':line})
   elif key=='watch' and line.startswith('MAX30102 '):
    matches=re.search(r'finger=(\w+) BPM=([^ ]+) dropped_batches=(\d+) gap=(\d+) fifo=([0-9/]+)',line)
    if matches:report[key].append({'elapsed_ms':round(elapsed*1000,2),'pulse_live':line.startswith('MAX30102 LIVE'),'finger':matches[1],'bpm_available':matches[2]!='--','dropped_batches':int(matches[3]),'gap_ms':int(matches[4]),'fifo':matches[5]})
 except Exception as error:report['errors'].append({'device':key,'error':type(error).__name__})
 finally:w.close()
threads=[threading.Thread(target=observe,args=('COM15','watch',['SENSORINFO','SCREENINFO'])),threading.Thread(target=observe,args=('COM8','hub',['HUBINFO']))]
for t in threads:t.start()
for t in threads:t.join()
report['completed_utc']=datetime.now(timezone.utc).isoformat()
OUT.write_text(json.dumps(report,indent=2),'utf8')
print(json.dumps({'watch_events':len(report['watch']),'hub_events':len(report['hub']),'errors':report['errors']}))
