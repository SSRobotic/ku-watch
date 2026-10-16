"""Repair only the Node-RED settings paths after the workspace was moved."""
from pathlib import Path
import json,re

root=Path(__file__).resolve().parents[1]
settings=Path.home()/'.node-red/settings-ku-watch.js'
text=settings.read_text(encoding='utf8')
count=0
def repair(match):
    global count
    value=json.loads(match[2]).replace('\\','/')
    for suffix in ['config/cloud.local.json','include/config.h']:
        if value.endswith('/KU_Watch_Display_First/'+suffix):
            after=json.dumps(str(root/suffix))
            if after!=match[2]:count+=1
            return match[1]+after
    return match[0]
text=re.sub(r'(fs\.readFileSync\()("[^"\n]*")',repair,text)
if count:
    backup=settings.with_name('settings-ku-watch.before-move-20261010.js')
    if not backup.exists():backup.write_bytes(settings.read_bytes())
    settings.write_text(text,encoding='utf8')
print(json.dumps({'paths_updated':count,'settings_backup_preserved':True}))
