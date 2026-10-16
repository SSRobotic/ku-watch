"""Allowlist a source handoff; fail closed on known local secret values."""
from pathlib import Path
import argparse,hashlib,json,re,zipfile
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/delivery_20261009'
TEXT={'.h','.hpp','.c','.cpp','.ino','.py','.cjs','.mjs','.js','.ps1','.cmd','.md','.csv','.ini','.json','.vue','.yaml','.txt','.xml','.xsd','.kicad_sch','.kicad_pro','.kicad_sym','.rpt'}
PRIVATE={'config.h','cloud_private.h','espnow_private.h','build_stamp.h'}
PUBLIC_LITERAL_FILES={'include/activity_recorder.h','include/face.h','tests/host/sensors.cpp','tests/host/telemetry.cpp','tests/test_activity_export.py','tests/test_influx_flow.cjs'}

def encode_public_literals(relative,data,secrets):
    # Keep ordinary digit alphabets and public CRC fixtures, even when a local
    # password coincides with their digits. Change spelling, not runtime value.
    if relative not in PUBLIC_LITERAL_FILES:return data
    source=data.decode('utf8')
    def literal(match):
        value=match[2]
        if not any(secret.decode() in value for secret in secrets):return match[0]
        if not value.isascii() or '\\' in value:raise RuntimeError('Unexpected public literal')
        return match[1]+''.join('\\x%02x'%ord(c) for c in value)+match[1]
    source=re.sub(r'''(["'])([^"'\n]*)\1''',literal,source)
    def hexadecimal(match):
        if any(secret.decode() in match[0] for secret in secrets):return str(int(match[1],16))+'ULL'
        return match[0]
    source=re.sub(r'0x([0-9a-fA-F]+)ULL',hexadecimal,source)
    return source.encode('utf8')
def known_secrets():
    values=set()
    def walk(value,key=''):
        if isinstance(value,dict):
            for k,v in value.items():walk(v,k)
        elif isinstance(value,str) and len(value)>=6 and any(s in key.lower() for s in ['password','token','secret','key','capability']):values.add(value.encode())
    for file in (ROOT/'config').glob('*.local.json'):walk(json.loads(file.read_text(encoding='utf8')))
    text=(ROOT/'include/config.h').read_text(encoding='utf8')
    for name,value in re.findall(r'constexpr char (\w+)\[\]\s*=\s*"([^"\n]*)"',text):
        if len(value)>=6 and ('PASSWORD' in name or 'TOKEN' in name or name=='WIFI_SSID'):values.add(value.encode())
    return values
def main():
    global OUT
    parser=argparse.ArgumentParser();parser.add_argument('--output-dir');args=parser.parse_args()
    if args.output_dir:OUT=ROOT/args.output_dir
    OUT.mkdir(parents=True,exist_ok=True)
    source=(ROOT/'include/config.h').read_text(encoding='utf8')
    source=re.sub(r'(constexpr char (?:WIFI_SSID|WIFI_PASSWORD|INFLUX_URL|INFLUX_ORG|INFLUX_BUCKET|INFLUX_TOKEN|MQTT_HOST|MQTT_USER|MQTT_PASSWORD)\[\]\s*=\s*)"(?:\\.|[^"\\])*"',lambda m:m[1]+'""',source)
    (ROOT/'include/config.example.h').write_text(source,encoding='utf8')
    secrets=known_secrets();payload={};blocked=[]
    candidates=list(ROOT.glob('*.md'))+list(ROOT.glob('*.csv'))+list((ROOT/'large_display').glob('*.md'))+[ROOT/'platformio.ini',ROOT/'partitions.csv',ROOT/'.gitignore']
    for directory in ['src','include','tools','tests','integration','large_display/KU_Hub','hardware/KU_Watch']:
        candidates.extend((ROOT/directory).rglob('*'))
    for file in sorted(set(candidates)):
        if not file.is_file():continue
        relative=file.relative_to(ROOT)
        if any(p in {'build','__pycache__','vendor','preview'} for p in relative.parts) or file.name in PRIVATE or '.local.' in file.name:continue
        if file.suffix not in TEXT and file.name!='.gitignore':continue
        data=encode_public_literals(relative.as_posix(),file.read_bytes(),secrets)
        if file.suffix=='.md':
            # Workspace output paths become portable links inside the source ZIP.
            data=data.replace(b'(output/presentation_evidence/',b'(presentation_evidence/')
            data=data.replace(b'(output/delivery_20261010/KU_Watch_',b'(presentation/KU_Watch_')
        if any(secret in data for secret in secrets):blocked.append(relative.as_posix());continue
        payload[relative.as_posix()]=data
    # These are public trust anchors required by platformio.ini, not private keys.
    for name in ['tools/certs/cacert.pem','tools/certs/x509_crt_bundle']:
        data=(ROOT/name).read_bytes()
        if b'PRIVATE KEY' in data or any(secret in data for secret in secrets):raise RuntimeError('CA bundle validation failed')
        payload[name]=data
    current_deck=ROOT/'output/canva_presentation_20261015/deliverable/KU_Watch_พร้อมนำเสนอ_15ตุลาคม2569_v2.pptx'
    deck=current_deck if current_deck.exists() else ROOT/'output/delivery_20261009/KU_Watch_ตามเกณฑ์ประเมิน_25691009_v2.pptx'
    with zipfile.ZipFile(deck) as presentation:
        if presentation.testzip():raise RuntimeError('Corrupt presentation')
        if any(secret in presentation.read(name) for name in presentation.namelist() for secret in secrets):raise RuntimeError('Presentation secret scan failed')
    payload['presentation/'+deck.name]=deck.read_bytes()
    slide_checks=ROOT/'output/presentation_build_latest/handoff_checks.json'
    if slide_checks.exists():
        data=slide_checks.read_bytes()
        if any(secret in data for secret in secrets):raise RuntimeError('Presentation check secret scan failed')
        payload['evidence/presentation_handoff_checks_20261010.json']=data
    for name in ['portal_acceptance.json','sensors_65s.json','hub_all_pages.json','completion_preserve_after.json','small_upload_v205.json','capture_storage.json','broker_outage.json','rtc_bridge_live.json']:
        data=(ROOT/'output/requirements_audit_20261009'/name).read_bytes()
        if any(secret in data for secret in secrets):raise RuntimeError('Evidence secret scan failed')
        payload['evidence/'+name]=data
    payload['evidence/alert_simulation.json']=(ROOT/'output/acceptance/alert_simulation.json').read_bytes()
    payload['evidence/acceptance_regression.json']=(ROOT/'output/acceptance/report.json').read_bytes()
    # A dated initial snapshot is evidence of a started audit, not its completion.
    soak=json.loads((ROOT/'output/soak_audit/status.json').read_text())
    payload['evidence/soak_at_delivery.json']=json.dumps(soak,indent=2).encode()
    for name in ['hub_pages_during_portal_probes.json','sensors_during_portal_probes.json']:
        payload['evidence/'+name]=(ROOT/'output/requirements_audit_20261009'/name).read_bytes()
    for name in ['clock_recovery_20261010.json','drain_database_final_20261010.json','live_recovery_20261010.json','small_upload_v206_20261010.json','preserve_v206_20261010.json','network_v206_drain_20261010.json','sensors_v206_20261010.json','v206_database_final_20261010.json',
                 'network_v206_final_20261010.json','network_hub_off_20261010.json','preserve_v207_20261010.json','network_v207_pause20_20261010.json','v207_pause20_database_20261010.json',
                 'wifi_ss_20261010.json','settings_ss_20261010.json','preserve_ss_20261010.json','network_ss_latest_20261010.json','ss_resumed_database_20261010.json',
                 'network_v208_final_20261010.json','network_v208_caught_up_20261010.json','preserve_v208_20261010.json','settings_v208_20261010.json','v208_database_final_20261010.json','sensors_v208_20261010.json','sensors_v208_live_20261010.json','live_v208_20261010.json','close_setup_v208_20261010.json',
                 'network_followup_20261010.json','network_after_latency_20261010.json','sensors_followup_20261010.json','followup_database_20261010.json','grafana_latency_exact_20261010.json','grafana_latency_clock_checked_20261010.json','host_clock_reference_20261010.json','host_clock_reference_fresh_20261010.json','grafana_config_20261010.json','grafana_runtime_20261010.json','followup_checks_20261010.json',
                 'grafana_runtime_before_restart_20261010.json','clock_reference_post_restart_20261010.json','grafana_latency_post_restart_20261010.json','live_followup_long_20261010.json','database_followup_long_20261010.json','network_followup_long_20261010.json','audit_coverage_checks_20261010.json','soak_restart_snapshot_20261010.json',
                 'soak_failed_followup_20261010.json','failed_soak_database_window_20261010.json','network_after_soak_gap_20261010.json',
                 'phone_network_transition_20261010.json','network_phone_20261010.json','replay_phone_20261010.json','network_pc_rescue_20261010.json','replay_pc_rescue_20261010.json','pc_rescue_database_20261010.json',
                 'network_phone_direct_20261010.json','replay_phone_direct_20261010.json','phone_direct_database_20261010.json','network_phone_drain_20261010.json','replay_phone_drain_20261010.json','live_phone_20261010.json','phone_drain_database_20261010.json',
                 'sensors_phone_live_20261010.json','clock_reference_phone_20261010.json','grafana_latency_phone_20261010.json','network_phone_final_20261010.json','soak_phone_start_20261010.json','soak_phone_at_delivery_20261010.json',
                 'network_phone_evidence_20261010.json','presentation_evidence_start_20261010.json']:
        evidence=ROOT/'output/requirements_audit_20261009'/name
        if evidence.exists():
            data=evidence.read_bytes()
            if any(secret in data for secret in secrets):raise RuntimeError('New evidence secret scan failed')
            payload['evidence/'+name]=data
    release=ROOT/'output/ota_release/2.0.8/release.json'
    if release.exists():payload['evidence/ota_release_2.0.8.json']=release.read_bytes()
    chart=ROOT/'output/delivery_20261009/ผลทดสอบ_MQTT_10นาที.png';payload['evidence/'+chart.name]=chart.read_bytes()
    # Timestamped rendered evidence reports are immutable snapshots, not screen captures.
    # Only verified layouts and their hash-matched public sources enter the handoff.
    gallery=ROOT/'output/presentation_evidence'
    allowed_sources={'soak_status.json','grafana_latency_phone_20261010.json','clock_reference_phone_20261010.json','phone_drain_database_20261010.json','live_phone_20261010.json','replay_phone_drain_20261010.json','network_phone_evidence_20261010.json','phone_network_transition_20261010.json'}
    allowed_images={'01_soak.png','02_query_latency.png','03_database.png','04_remaining.png'}
    verified_folders=set()
    for meta_file in sorted(gallery.glob('*/manifest.json')):
        folder=meta_file.parent
        if not re.fullmatch(r'\d{14}_(running|completed|failed|stopped)',folder.name):continue
        meta=json.loads(meta_file.read_text(encoding='utf8'))
        if not meta.get('layout_verified'):continue
        entries={**meta['sources'],**{item['file']:item for item in meta['images']}}
        if not set(meta['sources'])<=allowed_sources or not {item['file'] for item in meta['images']}<=allowed_images:raise RuntimeError('Unexpected gallery evidence file')
        public_files=[meta_file]
        for name,record in entries.items():
            file=folder/name;data=file.read_bytes()
            if hashlib.sha256(data).hexdigest()!=record['sha256']:raise RuntimeError('Gallery evidence hash mismatch')
            public_files.append(file)
            if name.endswith('.png'):public_files.append(file.with_suffix('.html'))
        for file in public_files:
            data=file.read_bytes()
            if any(secret in data for secret in secrets):raise RuntimeError('Gallery secret scan failed')
            payload['presentation_evidence/'+folder.name+'/'+file.name]=data
        verified_folders.add(folder.name)
    for name in ['index.html','latest.json','latest_soak.png','media/บันทึกภาพจริง.md']:
        file=gallery/name
        if file.exists():
            data=file.read_bytes()
            if any(secret in data for secret in secrets):raise RuntimeError('Gallery index secret scan failed')
            payload['presentation_evidence/'+name]=data
    timeline=gallery/'timeline.jsonl'
    if timeline.exists():
        rows=[json.loads(line) for line in timeline.read_text(encoding='utf8').splitlines() if line.strip()]
        rows=[row for row in rows if row['folder'] in verified_folders]
        data=('\n'.join(json.dumps(row,ensure_ascii=False) for row in rows)+'\n').encode('utf8')
        if any(secret in data for secret in secrets):raise RuntimeError('Gallery timeline secret scan failed')
        payload['presentation_evidence/timeline.jsonl']=data
    # Dated current observations are separate from the retained historical evidence.
    for relative in ['topic_migration.json','mqtt_5min_canonical.json','nvs_reboot.json','sensors_65s_after.json','hub_pages.json','script_checks.json','offline_10min/result.json']:
        file=ROOT/'output/final_acceptance_20261016'/relative
        if file.exists():
            data=file.read_bytes()
            if any(secret in data for secret in secrets):raise RuntimeError('Current evidence secret scan failed')
            payload['evidence/20261016/'+relative]=data
    payload['evidence/READ_FIRST.txt']=b'Current observations: 20261016/. Other evidence is dated history, including failed or partial tests, not blanket acceptance. Presentation snapshot: 20261015, before final acceptance updates. See the final Word checklist for current acceptance scope.'
    # Source archive is deliberately not a credential-bearing firmware backup.
    required=['include/config.example.h','src/main.cpp','include/setup_service.h','include/espnow_auth.h','include/activity_recorder.h','include/face.h','large_display/KU_Hub/KU_Hub.ino','tools/certs/x509_crt_bundle','ส่งมอบ_อ่านก่อน.md']
    if any(name not in payload for name in required):raise RuntimeError('Required source missing or blocked by secret scan')
    hashes={name:hashlib.sha256(data).hexdigest() for name,data in payload.items()}
    payload['DELIVERY_SHA256.json']=(json.dumps(hashes,indent=2,ensure_ascii=False)+'\n').encode()
    version=re.search(r'VERSION="([\d.]+)"',(ROOT/'include/watch_extensions.h').read_text())[1]
    hub_version=re.search(r'KU HUB ([\d.]+) boot:',(ROOT/'large_display/KU_Hub/KU_Hub.ino').read_text(encoding='utf8'))[1]
    target=OUT/('KU_Watch_Source_'+version+'_Hub_'+hub_version+'.zip')
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as archive:
        for name,data in payload.items():archive.writestr(name,data)
    with zipfile.ZipFile(target) as archive:
        if archive.testzip():raise RuntimeError('Corrupt source archive')
        for name in archive.namelist():
            data=archive.read(name)
            if any(secret in data for secret in secrets):raise RuntimeError('Secret scan failed')
            if name in hashes and hashlib.sha256(data).hexdigest()!=hashes[name]:raise RuntimeError('Hash verification failed')
    report={'archive':target.name,'files':len(payload),'bytes':target.stat().st_size,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'known_secret_scan_passed':True,'excluded_files_with_known_secrets':blocked,'firmware_images_included':False,'private_configs_included':False}
    (OUT/'manifest.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf8')
    print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
