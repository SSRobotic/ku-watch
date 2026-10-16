"""Package allowlisted FR evidence with portable names; leave originals untouched."""
from pathlib import Path
from datetime import datetime, timezone
from zipfile import ZipFile, ZIP_DEFLATED
import argparse, hashlib, json, shutil, time
from package_delivery import known_secrets

ROOT=Path(__file__).resolve().parents[1]
RUN=ROOT/'output/fr_completion_20261016'
parser=argparse.ArgumentParser();parser.add_argument('--revision',default='final15');args=parser.parse_args()
if not args.revision.isascii() or not args.revision.replace('_','').replace('-','').isalnum():raise ValueError('Portable revision required')
FW='2.0.15';SUFFIX='_'+args.revision
OUT=RUN/'deliverable'/args.revision
STAGE=RUN/('portable_handoff'+SUFFIX)
STAGE.mkdir(exist_ok=True)
payload={}

def add(src, name):
    src=Path(src)
    if not src.is_file(): raise FileNotFoundError(str(src))
    if name in payload: raise RuntimeError('Duplicate portable name')
    if not name.isascii() or '..' in Path(name).parts: raise RuntimeError('Unsafe portable path')
    for attempt in range(5):
        data=src.read_bytes()
        try:
            if src.suffix=='.json':json.loads(data.decode('utf-8-sig'))
            payload[name]=data
            return
        except (json.JSONDecodeError,UnicodeDecodeError):
            if attempt==4:raise
            time.sleep(.1)

for name in ['KU_Watch_FR_Status_'+FW+SUFFIX+'.docx','FR_Status_'+FW+SUFFIX+'.md','comparison.json']:
    add(OUT/name,name)
source=RUN/'source_handoff_final15/KU_Watch_Source_2.0.15_Hub_1.0.8.zip'
add(source,source.name)
add(RUN/'deliverable/media/FR06_Actual_Browser_Test.mp4','media/FR06_Actual_Browser_Test.mp4')
add(RUN/'deliverable/media/FR06_2.0.15_Actual_Browser_Test.mp4','media/FR06_2.0.15_Actual_Browser_Test.mp4')
latest_fr06=sorted((RUN/'fr06_runs').glob('*/fr06_hardware_browser.json'))[-1].parent
for capture in sorted(latest_fr06.glob('FR06_*.png')):add(capture,'media/FR06_2.0.15_'+capture.name)
add(RUN/'fr01_fr03_confirmed_2.0.15.json','evidence/fr01_fr03_confirmed_2.0.15.json')
for name in ['fr08_auto_update_2.0.15.json','fr08_mqtt_version_2.0.15.json',
             'user_visual_confirmation_2.0.12.json','user_visual_confirmation_2.0.15.json',
             'preserve_before_2.0.15.json','mqtt_2.0.15_pc_home_5min.json',
             'mqtt_pc_home_path.public.json','mqtt_pc_home_path_2.0.15.public.json','ppg_red_trial_20261016T142102Z.json',
             'ppg_headroom_trial_20261016T142752Z.json','mqtt_transport_analysis.json']:
    add(RUN/name,'evidence/'+name)
for name in ['fr08_auto_update_2.0.13.json','fr08_mqtt_version_2.0.13.json','user_visual_confirmation_2.0.13.json','mqtt_2.0.13_pc_home_5min.json','ppg_algorithm_change_2.0.14.json','ppg_summary_20261016T150838Z.json']:
    add(RUN/name,'evidence/'+name)
for pattern in ['fr08_auto_update_2.0.14_*.json','fr08_mqtt_version_2.0.14_*.json']:
    for attempt in sorted(RUN.glob(pattern)):add(attempt,'evidence/'+attempt.name)
for name in ['preserve_after_2.0.15.json','preservation_verified_2.0.15.json','user_visual_confirmation_2.0.14.json','fr08_auto_update_2.0.14.json','fr08_mqtt_version_2.0.14.json','mqtt_2.0.14_pc_home_5min.json']:
    if (RUN/name).exists():add(RUN/name,'evidence/'+name)
for name in ['preserve_after_2.0.14.json','preservation_verified_2.0.14.json']:
    if (RUN/name).exists():add(RUN/name,'evidence/'+name)
for attempt in sorted((RUN/'fr01_local_runs').glob('*/collection_failure.json')):
    add(attempt,'evidence/FR01_'+attempt.parent.name+'_collection_failure.json')
for attempt in sorted((RUN/'fr01_local_runs').glob('*/result.json')):
    add(attempt,'evidence/FR01_'+attempt.parent.name+'.json')
for attempt in sorted((RUN/'mqtt_transport_runs').glob('*/comparison.json')):
    add(attempt,'evidence/MQTT_'+attempt.parent.name+'.json')
add(RUN/'host_regressions/20261016T154226Z/report.json','evidence/host_assertions_enabled.json')
for name in ['preservation_verified_2.0.14_usb.json','preserve_after_2.0.14_usb.json']:
    if (RUN/name).exists():add(RUN/name,'evidence/'+name)

for name in ['fr08_auto_update.json','fr08_auto_update_2.0.12.json',
             'fr08_mqtt_version.json','fr08_mqtt_version_2.0.12.json',
             'watch_network_display_2.0.12.json','hub_network_2.0.12.json',
             'preserve_before_upgrade.json','preserve_after_2.0.12.json',
             'preservation_verified_2.0.12.json','bootstrap_upgrade.json',
             'mqtt_2.0.11_5min.json','mqtt_2.0.12_5min_monotonic.json',
             'mqtt_2.0.12_normal_5min.json',
             'fr01_active_status.json','sensors_finger_current_65s.json',
             'sensors_2.0.12_baseline_65s.json']:
    add(RUN/name,'evidence/'+name)
add(RUN/'mqtt_path_diagnostics.public.json','evidence/mqtt_path_diagnostics.json')

add(RUN/'fr06_hardware_browser.json','evidence/FR06_2.0.10_failed.json')
for attempt in sorted((RUN/'fr06_runs').iterdir()):
    if not attempt.is_dir():continue
    add(attempt/'fr06_hardware_browser.json','evidence/FR06_'+attempt.name+'.json')
final=RUN/'fr06_runs/2026-10-16T13-19-09-155Z'
add(final/'FR06_TEMP_156752045.png','media/FR06_TEMP_Actual_Browser.png')
add(final/'FR06_IAQ_156761320.png','media/FR06_IAQ_Actual_Browser.png')

active=json.loads((RUN/'fr01_active_status.json').read_text())
add(active['result'],'evidence/FR01_observer_snapshot.json')
add(ROOT/'output/accumulated_soak/status.json','evidence/MQTT_soak_snapshot.json')
add(ROOT/'output/soak_audit/status.json','historical/failed_soak_original.json')
add(RUN/'host_regressions/report.json','evidence/host_regression_initial_report.json')
add(RUN/'host_regressions/pulse_25hz_retry_result.json','evidence/host_pulse_25hz_retry_result.json')
base=ROOT/'output/final_acceptance_20261016'
for src,name in [('mqtt_5min_canonical.json','FR03_2.0.9_5min.json'),
                 ('offline_10min/result.json','FR05_NFR02_2.0.9_offline_10min.json'),
                 ('nvs_reboot.json','FR07_2.0.9_NVS_reboot.json')]:
    add(base/src,'historical/'+name)

secrets=known_secrets()
for name,data in payload.items():
    if name.endswith(('.docx','.zip')):
        from io import BytesIO
        with ZipFile(BytesIO(data)) as z:
            if z.testzip() is not None: raise RuntimeError('Corrupt nested Office/ZIP')
            for entry in z.namelist():
                content=z.read(entry)
                if any(secret in content for secret in secrets):
                    raise RuntimeError('Known local secret in nested artifact')
    elif any(secret in data for secret in secrets):
        raise RuntimeError('Known local secret in portable payload')
    if name.endswith(('.json','.md','.txt')) and b'PRIVATE KEY-----' in data:
        raise RuntimeError('Private key in evidence')

manifest={'created_utc':datetime.now(timezone.utc).isoformat(),
          'scope':'Actual observed results with failed attempts retained; unresolved requirements remain unresolved.',
          'known_local_secret_scan_passed':True,
          'files':[{'path':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
                   for name,data in sorted(payload.items())]}
payload['manifest.json']=json.dumps(manifest,ensure_ascii=False,indent=2).encode('utf8')

payload['READ_FIRST.txt']=(f'KU Watch FR evidence, watch {FW}, hub 1.0.8\r\n'
    f'Open KU_Watch_FR_Status_{FW}{SUFFIX}.docx for the original-criteria checklist.\r\n'
    f'FR_Status_{FW}{SUFFIX}.md explains the current results in Thai.\r\n'
    'Both successful and failed real tests are retained. Read comparison.json for current acceptance.\r\n'
    'FR-06 uses permitted isolated simulated input. FR-08 was automatic HTTPS OTA; both displays confirmed.\r\n'
    'Earlier dated firmware tests are historical, not retests of 2.0.14.\r\n'
    'Use host_assertions_enabled.json for actual host-test proof.\r\n'
    'Cumulative MQTT time does not prove continuous 24h operation or battery endurance.\r\n'
    'Private configs, TLS keys, device flash backup and firmware binaries are excluded.\r\n').encode('ascii')
for name,data in payload.items():
    target=STAGE/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
zip_path=RUN/('KU_Watch_FR_'+FW+SUFFIX+'.zip')
if zip_path.exists():raise FileExistsError('Preserve earlier delivery; choose a new revision')
with ZipFile(zip_path,'w',compression=ZIP_DEFLATED,compresslevel=6,allowZip64=True) as z:
    for name,data in sorted(payload.items()):z.writestr(name,data)
with ZipFile(zip_path) as z:
    assert z.testzip() is None
    assert set(z.namelist())==set(payload)
    for name,data in payload.items():assert z.read(name)==data

downloads=Path('C:/Users/pomma/Downloads')
published_zip=downloads/zip_path.name
published_dir=downloads/('KU_Watch_FR_'+FW+SUFFIX)
published_dir.mkdir(exist_ok=True)
for name,data in payload.items():
    target=published_dir/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
shutil.copy2(zip_path,published_zip)
assert published_zip.read_bytes()==zip_path.read_bytes()
published_doc=downloads/('KU_Watch_FR_Status_'+FW+SUFFIX+'.docx')
shutil.copy2(OUT/published_doc.name,published_doc)
result={'zip':str(published_zip),'extracted':str(published_dir),'docx':str(published_doc),
        'files':len(payload),'zip_bytes':zip_path.stat().st_size,
        'zip_sha256':hashlib.sha256(zip_path.read_bytes()).hexdigest(),
        'portable_paths_ascii':True,'max_internal_path_chars':max(map(len,payload)),
        'crc_and_every_file_verified':True,'known_local_secret_scan_passed':True,
        'no_private_configs_keys_or_flash_images_included':True}
(RUN/('handoff_verified'+SUFFIX+'.json')).write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps(result,ensure_ascii=False))
