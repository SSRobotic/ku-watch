"""Verify all six zoom levels over the actual paired hub/watch radio link."""
from pathlib import Path
from datetime import datetime,timezone
import json,re,time
import serial

root=Path(__file__).resolve().parents[1];out=root/'output/map_zoom_20261014'
target=out/'device_zoom_acceptance.json'
if target.exists():raise FileExistsError('Retain the earlier device audit')
port=serial.Serial();port.port='COM8';port.baudrate=115200;port.timeout=.1;port.dtr=False;port.rts=False;port.open()
report={'started_utc':datetime.now(timezone.utc).isoformat(),'boundary':'Actual USB hub commands, matching watch telemetry and radio ACKs. Does not measure physical touch latency or GPS accuracy.','levels':[]}
def query(command,seconds=1.5):
    port.write((command+'\n').encode());until=time.monotonic()+seconds;lines=[]
    while time.monotonic()<until:
        line=port.readline().decode('ascii','replace').strip()
        if line.startswith(('HUBINFO ','HUB ACK ','HUB CLOCK ','HUB SD ','HUB COMMAND ')):lines.append(line)
    return lines
def state(lines):
    rows=[dict(re.findall(r'(\w+)=([^ ]+)',x)) for x in lines if x.startswith('HUBINFO ')]
    return rows[-1] if rows else {}
try:
    before={}
    for attempt in range(12):
        lines=query('HUBINFO',1.5);before=state(lines)
        if before.get('receiver')=='1':break
    report['before']=before
    if before.get('version')!='1.0.8' or before.get('receiver')!='1':raise RuntimeError('Updated fresh hub/watch pair required')
    report['page_command']=query('PAGE 6',2)
    for level,meters in [(0,100),(1,250),(2,500),(3,1000),(4,50),(5,25)]:
        lines=query('LINKCMD 7 '+str(level),1.5)+query('HUBINFO',1)
        current=state(lines)
        passed=current.get('receiver')=='1' and current.get('zoom')==str(level) and current.get('watchpage')=='6'
        row={'zoom_index':level,'scale_bar_m':meters,'passed':passed,'status':current,'lines':lines};report['levels'].append(row)
        print('Zoom',meters,'m:',passed,flush=True)
        if not passed:raise RuntimeError('Zoom command not reflected by watch')
    report['final']=query('HUBINFO',1.5)
    if not any('firmware=2.0.9' in line for line in report['final']):raise RuntimeError('Watch version does not match reviewed image')
    report['passed']=True;report['final_zoom_m']=25
finally:
    port.close();report['finished_utc']=datetime.now(timezone.utc).isoformat();target.write_text(json.dumps(report,indent=2),encoding='utf8')
print('Both devices show the 25 m zoom level in matching radio telemetry.')
