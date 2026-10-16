"""Back up full private flash, verify identity/partitions, update only app0."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,shutil,subprocess
from activity_export import Watch
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/fr_completion_20261016'
python=Path.home()/'.platformio/penv/Scripts/python.exe'
esptool=Path.home()/'.platformio/packages/tool-esptoolpy/esptool.py'
report_path=OUT/'bootstrap_upgrade.json'
if report_path.exists():raise FileExistsError('Do not overwrite upgrade evidence')
before=json.loads((OUT/'preserve_before_upgrade.json').read_text())
assert before['recording']==0 and len(before['activity_files'])==6
watch=Watch('COM15')
try:assert watch.status()['active']==0
finally:watch.close()
image=ROOT/'.pio/build/display_first/firmware.bin'
assert b'2.0.10\0' in image.read_bytes() and image.read_bytes()[0]==0xe9
shutil.copyfile(image,OUT/'firmware_2.0.10.bin')
shutil.copyfile(ROOT/'output/accumulated_soak/status.json',OUT/'soak_before_bootstrap.json')
report={'started_utc':datetime.now(timezone.utc).isoformat(),'firmware_sha256':hashlib.sha256(image.read_bytes()).hexdigest(),'steps':[],'filesystem_erased':False,'nvs_erased':False,'app0_only':True}
def save():report_path.write_text(json.dumps(report,indent=2),'utf8')
def run(name,tail):
    print(name,flush=True)
    result=subprocess.run([str(python),str(esptool),'--chip','esp32s3','--port','COM15','--baud','921600',*map(str,tail)],cwd=ROOT,capture_output=True,text=True)
    (OUT/(name+'.private.log')).write_text(result.stdout+result.stderr,'utf8')
    report['steps'].append({'operation':name,'exit_code':result.returncode,'finished_utc':datetime.now(timezone.utc).isoformat()});save()
    if result.returncode:raise RuntimeError(name+' failed; private log retained')
    return result.stdout
save()
identity=run('bootstrap_identity',['read_mac'])
assert 'd4:05:92:44:51:ac' in identity.lower(),'Unexpected device identity'
backup=OUT/'watch_flash_before.private.bin'
assert not backup.exists()
run('bootstrap_flash_backup',['read_flash','0','0x400000',backup])
raw=backup.read_bytes();assert len(raw)==4194304
partitions=(ROOT/'.pio/build/display_first/partitions.bin').read_bytes()
assert raw[0x8000:0x8000+len(partitions)]==partitions,'Partition map changed; stop before writing'
report['backup_sha256']=hashlib.sha256(raw).hexdigest();save()
run('bootstrap_app0_write',['write_flash','0x10000',OUT/'firmware_2.0.10.bin'])
report['completed_utc']=datetime.now(timezone.utc).isoformat();report['app0_written']=True;save()
print(json.dumps({k:v for k,v in report.items() if k!='steps'}))
