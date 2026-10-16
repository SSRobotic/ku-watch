"""Read-only USB settings and activity-file verification around the zoom update."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, json, re, time
from activity_export import Watch

root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('stage',choices=['before','after']);p.add_argument('--output');a=p.parse_args()
out=root/'output/map_zoom_20261014';target=out/(a.output or ('watch_'+a.stage+'_upload.json'))
if target.exists():raise FileExistsError('Preserve the earlier upload audit')
w=Watch('COM15');report={'checked_utc':datetime.now(timezone.utc).isoformat(),'port':'COM15','stage':a.stage,'activities':{},'complete':False}
def query(text):
    w.send(text);lines=[];until=time.monotonic()+.9
    while time.monotonic()<until:
        line=w.serial.readline().decode('utf8','replace').strip()
        if line.startswith(('SETTINGS ','OTA ','CLOCK ','SCREEN ','LCD ','ESPNOW ')):lines.append(line)
    return lines
try:
    report['recording']=w.status()
    if report['recording']['active']:raise RuntimeError('WALK is still active; upload not started')
    for cmd in ['SETTINGSINFO','OTAINFO','CLOCKINFO','LINKINFO','SCREENINFO']:report[cmd]=query(cmd)
    report['file_list']=w.list()
    for identity,size in report['file_list']:
        raw=w.download(identity);assert len(raw)==size
        report['activities'][str(identity)]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
        if a.stage=='before':
            f=out/'activity_backup'/f'rec{identity:06d}.kua';f.parent.mkdir(exist_ok=True)
            if f.exists() and f.read_bytes()!=raw:raise RuntimeError('Prior activity backup differs')
            f.write_bytes(raw)
    if a.stage=='after':
        before_file=out/'watch_before_upload_complete.json'
        before=json.loads((before_file if before_file.exists() else out/'watch_before_upload.json').read_text())
        def settings(d):
            line=next(x for x in d['SETTINGSINFO'] if x.startswith('SETTINGS '))
            return {k:v for k,v in re.findall(r'(\w+)=([^ ]+)',line) if k!='restored'}
        report['settings_unchanged']=settings(before)==settings(report)
        report['activities_unchanged']=before['activities']==report['activities']
        if not report['settings_unchanged'] or not report['activities_unchanged']:raise RuntimeError('Preservation check differs')
    report['complete']=True
finally:
    w.close();target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(report,ensure_ascii=False))
