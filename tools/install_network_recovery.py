"""Install a locally built OTA image; preserve activity hashes and never set time."""
import base64,hashlib,json,time,urllib.request
from pathlib import Path
from activity_export import Watch
ROOT=Path(__file__).resolve().parents[1]
w=Watch('COM15');result={};opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def portal():
    w.send('SETUP');time.sleep(1)
    w.send('SETUPAUTH');end=time.monotonic()+5
    while time.monotonic()<end:
        line=w.serial.readline().decode(errors='replace').strip()
        if line.startswith('SETUPAUTH '):
            ip,password=line.split()[1:];return 'http://'+ip,password
    raise RuntimeError('Authenticated setup portal not available')
def get(url,password,path):
    auth='Basic '+base64.b64encode(('admin:'+password).encode()).decode()
    with opener.open(urllib.request.Request(url+'/'+path,headers={'Authorization':auth}),timeout=20) as r:return r.read()
def hashes(url,password):
    manifest=json.loads(get(url,password,'activities'))
    if manifest['active']:raise RuntimeError('An activity is recording; update was not started')
    return {str(f['id']):hashlib.sha256(get(url,password,'activity?id='+str(f['id']))).hexdigest() for f in manifest['files']}
try:
    url,password=portal();before=hashes(url,password)
    firmware=(ROOT/'.pio/build/display_first/firmware.bin').read_bytes();boundary='KuWatchNetworkRecovery'
    body=(f'--{boundary}\r\nContent-Disposition: form-data; name="firmware"; filename="firmware.bin"\r\nContent-Type: application/octet-stream\r\n\r\n').encode()+firmware+f'\r\n--{boundary}--\r\n'.encode()
    auth='Basic '+base64.b64encode(('admin:'+password).encode()).decode()
    req=urllib.request.Request(url+'/update?token='+password,data=body,headers={'Authorization':auth,'Content-Type':'multipart/form-data; boundary='+boundary})
    with opener.open(req,timeout=60) as response:result['http']=response.status;result['response']=response.read().decode()
    time.sleep(8);url,password=portal();after=hashes(url,password)
    status=json.loads(get(url,password,'status'))
    result.update(version=status.get('firmware'),activity_hashes_unchanged=before==after,activity_ids=list(after),firmware_sha256=hashlib.sha256(firmware).hexdigest(),clock_set_by_tool=False)
    (ROOT/'config/watch-access.local.json').write_text(json.dumps({'url':url,'username':'admin','password':password,'watch_mac':'D4:05:92:44:51:AC'}))
finally:w.close()
(ROOT/'output/requirements_audit_20261009/network_update_20261010.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
