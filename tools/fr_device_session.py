"""Private local device access and preservation helpers; no credential output."""
from pathlib import Path
from datetime import datetime,timezone
import base64,hashlib,html,json,re,time,urllib.request,urllib.parse
from activity_export import Watch
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/fr_completion_20261016'
ACCESS=ROOT/'config/watch-access.local.json'

def usb(commands,seconds=.65):
    device=Watch('COM15');result=[]
    try:
        for command in commands:
            device.send(command);deadline=time.monotonic()+seconds
            while time.monotonic()<deadline:
                line=device.serial.readline().decode('ascii','replace').strip()
                if line.startswith('SETUPAUTH '):
                    parts=line.split()
                    if len(parts)==3 and re.fullmatch(r'[0-9.]+',parts[1]) and parts[1]!='0.0.0.0':
                        old=json.loads(ACCESS.read_text()) if ACCESS.exists() else {}
                        old.update(url='http://'+parts[1],username='admin',password=parts[2]);ACCESS.write_text(json.dumps(old),'utf8')
                elif line.startswith(('OTA ','OTAINFO ','SETTINGS ','SCREEN ','ALERT ','ALERTTEST ','RATES ','REBOOT ','REC STATUS ','NETWORK ','QUEUE ','CLOCK ','PPGQUALITY ','SENSORS ')):
                    result.append(line)
    finally:device.close()
    return result

def request(route='',form=None):
    access=json.loads(ACCESS.read_text());auth=base64.b64encode((access['username']+':'+access['password']).encode()).decode()
    data=None if form is None else urllib.parse.urlencode({**form,'token':access['password']}).encode()
    req=urllib.request.Request(access['url'].rstrip('/')+'/'+route,data=data,headers={'Authorization':'Basic '+auth})
    with urllib.request.urlopen(req,timeout=12) as response:return response.read()

def open_portal():
    usb(['SETUP'],1);usb(['SETUPAUTH'],1)
    return json.loads(request('status'))

def close_portal():
    request('close',{})

def fields():
    return {key:html.unescape(value) for key,value in re.findall(r"name='([^']+)'[^>]*value=\"([^\"]*)\"",request().decode())}

def preserve(stage):
    status=open_portal();setting=fields();listing=json.loads(request('activities'))
    if listing['active']:raise RuntimeError('WALK recording active; preserve and defer upgrade')
    records={}
    for item in listing['files']:
        data=request('activity?id='+str(item['id']))
        records[str(item['id'])]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
    stable={key:value for key,value in setting.items() if key!='manifest'}
    report={'checked_utc':datetime.now(timezone.utc).isoformat(),'firmware':status['firmware'],'settings_excluding_manifest_sha256':hashlib.sha256(json.dumps(stable,sort_keys=True).encode()).hexdigest(),'activity_files':records,'recording':listing['active'],'private_settings_logged':False,'raw_activity_data_saved':False}
    target=OUT/('preserve_'+stage+'.json')
    if target.exists():raise FileExistsError('Keep prior preservation evidence')
    target.write_text(json.dumps(report,indent=2),'utf8');close_portal();print(json.dumps(report))
    return report

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--preserve',required=True);a=p.parse_args();preserve(a.preserve)
