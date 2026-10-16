"""Hash existing activities in memory when the watch HTTP LAN is unavailable."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json
from activity_export import Watch
from fr_device_session import usb

ROOT=Path(__file__).resolve().parents[1]
RUN=ROOT/'output/fr_completion_20261016'
p=argparse.ArgumentParser();p.add_argument('--version',default='2.0.13');a=p.parse_args()
target=RUN/('preserve_after_'+a.version+'_usb.json')
verified=RUN/('preservation_verified_'+a.version+'_usb.json')
if target.exists() or verified.exists():raise FileExistsError('Keep earlier evidence')
before=json.loads((RUN/('preserve_before_'+a.version+'.json')).read_text())
diagnostics=usb(['OTAINFO','SETTINGSINFO'],1)
device=Watch('COM15')
try:
    status=device.status()
    if status['active']:raise RuntimeError('Do not read active recording as stable evidence')
    files={}
    for identity,size in device.list():
        data=device.download(identity)
        if len(data)!=size:raise RuntimeError('USB activity length mismatch')
        files[str(identity)]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
finally:device.close()
report={'checked_utc':datetime.now(timezone.utc).isoformat(),'transport':'USB read only',
        'firmware':a.version,'activity_files':files,'recording':status['active'],
        'raw_activity_data_saved':False,'private_settings_logged':False,
        'visible_settings_diagnostics':[x for x in diagnostics if x.startswith(('OTA ','SETTINGS '))],
        'full_settings_hash_compared':False,
        'settings_scope':'Only non-secret serial settings inspected; full HTTP settings comparison unavailable across separate PC network'}
target.write_text(json.dumps(report,indent=2),'utf8')
result={'checked_utc':report['checked_utc'],'version':a.version,
        'activity_count':len(files),'all_activity_hashes_and_sizes_match':files==before['activity_files'],
        'full_settings_hash_compared':False,'evidence':target.name,
        'before_evidence_sha256':hashlib.sha256((RUN/('preserve_before_'+a.version+'.json')).read_bytes()).hexdigest()}
verified.write_text(json.dumps(result,indent=2),'utf8')
print(json.dumps(result))
