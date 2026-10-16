"""Set authorized Wi-Fi through the existing authenticated portal; keep all other settings.
Credentials are read from local config and are never printed. Temporarily joins the
watch AP, then restores the computer's saved connection even on failure.
"""
from pathlib import Path
import argparse,base64,html,json,re,subprocess,time,urllib.parse,urllib.request
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--output',default='output/requirements_audit_20261009/wifi_change_20261010.json');args=parser.parse_args()
config=json.loads((ROOT/'config/wifi-replacement.local.json').read_text())
access=json.loads((ROOT/'config/watch-access.local.json').read_text())
profile='KU-WATCH-05D4'
xml=ROOT/'config/watch-wlan.local.xml'
xml.write_text('<?xml version="1.0"?><WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1"><name>'+profile+'</name><SSIDConfig><SSID><name>'+profile+'</name></SSID></SSIDConfig><connectionType>ESS</connectionType><connectionMode>manual</connectionMode><MSM><security><authEncryption><authentication>WPA2PSK</authentication><encryption>AES</encryption><useOneX>false</useOneX></authEncryption><sharedKey><keyType>passPhrase</keyType><protected>false</protected><keyMaterial>'+html.escape(access['password'])+'</keyMaterial></sharedKey></security></MSM></WLANProfile>')
auth='Basic '+base64.b64encode((access['username']+':'+access['password']).encode()).decode()
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def request(url,data=None):
    with opener.open(urllib.request.Request(url,data=data,headers={'Authorization':auth}),timeout=3) as r:return r.read()
report={'settings_saved':False,'computer_wifi_restored':False}
try:
    subprocess.run(['netsh','wlan','add','profile','filename='+str(xml),'user=current'],capture_output=True,check=True)
    xml.unlink()
    subprocess.run(['netsh','wlan','connect','name='+profile,'ssid='+profile],capture_output=True,check=True)
    for attempt in range(20):
        try:page=request('http://192.168.4.1/').decode();break
        except OSError:time.sleep(1)
    else:raise RuntimeError('Watch setup AP not reachable')
    form={k:html.unescape(v) for k,v in re.findall(r"name='([^']+)'[^>]*value=\"([^\"]*)\"",page)}
    form.update(ssid=config['ssid'],password=config['password'],token=access['password'])
    request('http://192.168.4.1/save',urllib.parse.urlencode(form).encode())
    report['settings_saved']=True;report['ssid']=config['ssid']
    time.sleep(2)
finally:
    subprocess.run(['netsh','wlan','connect','name='+config['restore_profile']],capture_output=True)
    report['computer_wifi_restored']=True
    subprocess.run(['netsh','wlan','delete','profile','name='+profile],capture_output=True)
    xml.unlink(missing_ok=True)
    (ROOT/args.output).write_text(json.dumps(report,indent=2))
    print(json.dumps(report))
