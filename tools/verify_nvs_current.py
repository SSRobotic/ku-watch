"""Verify real NVS after changing safe settings and reboot; restore user limits."""
from pathlib import Path
from datetime import datetime,timezone
import base64,hashlib,html,json,re,time,urllib.request,urllib.parse
from activity_export import Watch
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/final_acceptance_20261016';target=OUT/'nvs_reboot.json'
if target.exists():raise FileExistsError('Keep prior NVS evidence')
def usb(commands,seconds=.7):
 w=Watch('COM15');result=[]
 try:
  for command in commands:
   w.send(command);until=time.monotonic()+seconds
   while time.monotonic()<until:
    line=w.serial.readline().decode('ascii','replace').strip()
    if line.startswith('SETUPAUTH '):
     parts=line.split();p=ROOT/'config/watch-access.local.json';v=json.loads(p.read_text());v.update(url='http://'+parts[1],username='admin',password=parts[2]);p.write_text(json.dumps(v),encoding='utf8')
    elif line.startswith(('REBOOT ','SETTINGS ','ALERT ','CLOCK ')):result.append(line)
 finally:w.close()
 return result
def request(route,data=None):
 v=json.loads((ROOT/'config/watch-access.local.json').read_text());auth='Basic '+base64.b64encode((v['username']+':'+v['password']).encode()).decode()
 with urllib.request.urlopen(urllib.request.Request(v['url'].rstrip('/')+'/'+route,data=data,headers={'Authorization':auth}),timeout=5) as r:return r.read()
def fields():return {k:html.unescape(v) for k,v in re.findall(r"name='([^']+)'[^>]*value=\"([^\"]*)\"",request('').decode())}
def status():return json.loads(request('status'))
def save(f):
 v=json.loads((ROOT/'config/watch-access.local.json').read_text());form=dict(f);form['token']=v['password'];request('save',urllib.parse.urlencode(form).encode())
def fingerprint(f):return hashlib.sha256(json.dumps(f,sort_keys=True).encode()).hexdigest()
def activities():
 data=json.loads(request('activities'))
 if data['active']:raise RuntimeError('Active WALK')
 return {str(x['id']):{'bytes':x['size']} for x in data['files']}
def reboot_online():
 before=status();usb(['REBOOT'],.4);time.sleep(5);deadline=time.monotonic()+65
 while time.monotonic()<deadline:
  try:
   usb(['SETUP','SETUPAUTH'],.6);s=status()
   if s['wifi'] and s['mqtt'] and s['uptime_ms']<before['uptime_ms']:return s
  except Exception:pass
  time.sleep(2)
 raise RuntimeError('Did not rejoin automatically after reboot')
r={'started_utc':datetime.now(timezone.utc).isoformat(),'boundary':'Real settings form + two software reboots, not OTA power-cut/rollback testing','activity_check_boundary':'File IDs and byte sizes only; no raw coordinates saved or content hash claimed','passed':False}
original=None
try:
 original=fields();r['before_status']=status();r['before_activities']=activities();r['original_settings_sha256']=fingerprint(original)
 changed=dict(original);changed['temperature_limit']='35.50';changed['iaq_limit']='151.00';save(changed);r['changed_fields']=['MQTT topic from coordinated migration','temperature_limit','iaq_limit'];r['after_change_status']=status()
 r['first_reboot']=reboot_online();readback=fields();r['changed_limits_persisted']=readback['temperature_limit']=='35.50' and readback['iaq_limit']=='151.00';r['network_settings_persisted']=all(readback[k]==original[k] for k in ['ssid','host','port','tls','user','topic'])
 if not r['changed_limits_persisted'] or not r['network_settings_persisted']:raise RuntimeError('NVS readback mismatch')
 save(original);r['second_reboot']=reboot_online();r['restored_original_settings']=fingerprint(fields())==r['original_settings_sha256'];r['after_activities']=activities();r['activities_unchanged']=r['before_activities']==r['after_activities'];r['diagnostics']=usb(['SETTINGSINFO','ALERTINFO','CLOCKINFO'])
 r['passed']=r['restored_original_settings'] and r['activities_unchanged'] and r['changed_limits_persisted'] and r['network_settings_persisted'];r['restored']=True
except Exception as e:
 r['error']=type(e).__name__;r['reason']=str(e)[:180]
 if original:
  try:save(original);r['restored']=True
  except Exception:r['restored']=False
finally:
 r['finished_utc']=datetime.now(timezone.utc).isoformat();target.write_text(json.dumps(r,indent=2),encoding='utf8');print(json.dumps({k:v for k,v in r.items() if k not in ['before_activities','after_activities']}))
raise SystemExit(0 if r['passed'] else 1)
