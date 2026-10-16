"""Install the reviewed map-zoom images on the two verified USB devices."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib,json,subprocess,sys

root=Path(__file__).resolve().parents[1];out=root/'output/map_zoom_20261014'
report_path=out/'usb_install.json'
if report_path.exists():raise FileExistsError('Do not overwrite an earlier install report')
python=Path.home()/'.platformio/penv/Scripts/python.exe'
esptool=Path.home()/'.platformio/packages/tool-esptoolpy/esptool.py'
manifest=json.loads((out/'manifest.json').read_text())
before=json.loads((out/'watch_before_upload_complete.json').read_text())
if not before.get('complete'):raise RuntimeError('Complete activity preservation audit required')
if before['recording']['active']:raise RuntimeError('WALK active; no upload')
report={'started_utc':datetime.now(timezone.utc).isoformat(),'steps':[],'watch_uploaded':False,'hub_uploaded':False,'storage_erased':False}
def save():report_path.write_text(json.dumps(report,indent=2),encoding='utf8')
def run(name,args):
    print(name,flush=True)
    result=subprocess.run([str(x) for x in args],cwd=root,capture_output=True,text=True)
    (out/(name+'.log')).write_text(result.stdout+result.stderr,encoding='utf8')
    report['steps'].append({'name':name,'exit_code':result.returncode,'finished_utc':datetime.now(timezone.utc).isoformat()});save()
    if result.returncode:raise RuntimeError(name+' failed; see local log')
    return result.stdout+result.stderr
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
try:
    for image in manifest['firmware']:
        if digest(out/image['file'])!=image['sha256']:raise RuntimeError('Reviewed image changed')
    for board,port,mac in [('watch','COM15','d4:05:92:44:51:ac'),('hub','COM8','28:84:85:88:0b:0c')]:
        result=run(board+'_identity',[python,esptool,'--port',port,'read_mac'])
        if mac not in result.lower():raise RuntimeError('Unexpected '+board+' hardware identity')
    backup=out/'watch_flash_before.bin'
    if backup.exists():raise FileExistsError('Preserve flash backup')
    run('watch_backup',[python,esptool,'--port','COM15','--baud','460800','read_flash','0','0x400000',backup])
    raw=backup.read_bytes()
    if len(raw)!=4194304:raise RuntimeError('Incomplete watch backup')
    partitions=(root/'.pio/build/display_first/partitions.bin').read_bytes()
    if raw[0x8000:0x8000+len(partitions)]!=partitions:raise RuntimeError('Existing partition map differs; stopped before writing')
    report['backup_sha256']=digest(backup);save()
    image=out/manifest['firmware'][0]['file']
    boot=Path.home()/'.platformio/packages/framework-arduinoespressif32/tools/partitions/boot_app0.bin'
    # Select app0 and write that app only. Leave NVS, filesystem and app1 intact.
    run('watch_upload',[python,esptool,'--port','COM15','--baud','460800','write_flash','0xe000',boot,'0x10000',image])
    report['watch_uploaded']=True;save()
    hub=next(x for x in manifest['firmware'] if x['board']=='hub')
    if digest(root/'output/large_build_artifacts/KU_Hub.ino.bin')!=hub['sha256']:raise RuntimeError('Hub input differs from reviewed image')
    run('hub_upload',[python,root/'tools/build_large.py','--upload','--port','COM8'])
    report['hub_uploaded']=True
finally:
    report['finished_utc']=datetime.now(timezone.utc).isoformat();save()
print(json.dumps(report,indent=2))
