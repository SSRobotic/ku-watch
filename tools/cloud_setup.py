"""Local-only masked credential entry; prepares firmware and existing Node-RED."""
from pathlib import Path
import json
import re
import shutil
import subprocess
import sys
import time
import tkinter as tk
from tkinter import ttk, messagebox

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT/'config/cloud.local.json'
HOST = '4047191cd08c4f91b9c3274b30881bc6.s1.eu.hivemq.cloud'

def validate(data):
    host=data['host'].strip().lower()
    if not re.fullmatch(r'[a-z0-9-]+(?:\.[a-z0-9-]+)*\.hivemq\.cloud',host):
        raise ValueError('ใส่ชื่อเซิร์ฟเวอร์ .hivemq.cloud โดยไม่ใส่ https:// หรือเลขพอร์ต')
    for key in ['watch_user','watch_password','reader_user','reader_password']:
        if not data.get(key) or any(ord(c)<32 for c in data[key]):
            raise ValueError('กรอกชื่อผู้ใช้และรหัสผ่าน MQTT ทั้งสองบัญชีให้ครบ')
    return dict(data,host=host,enabled=True)

def prepare(data, activate=False):
    """No service restart, network transmission, build, or flash from this function."""
    (ROOT/'config').mkdir(exist_ok=True)
    LOCAL.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    header='#pragma once\n// Private. Do not share or commit this file.\n'
    header+='#define KU_CLOUD_ENABLED '+('true' if data.get('enabled') else 'false')+'\n'
    for macro,key in [('HOST','host'),('USER','watch_user'),('PASSWORD','watch_password')]:
        header+='#define KU_CLOUD_'+macro+' '+json.dumps(data.get(key,''),ensure_ascii=True)+'\n'
    (ROOT/'include/cloud_private.h').write_text(header,encoding='utf-8')
    userdir=Path.home()/'.node-red'
    flows_path=userdir/'flows.json'
    flows=json.loads(flows_path.read_text(encoding='utf-8-sig'))
    backup=userdir/'ku-watch-backups'/time.strftime('%Y%m%d-%H%M%S')
    backup.mkdir(parents=True,exist_ok=True)
    for name in ['flows.json','flows_cred.json','settings.js']:
        src=userdir/name
        if src.exists(): shutil.copy2(src,backup/name)
    # Preserve existing dashboard and credentials. Switch its MQTT source, not its fields.
    flows=[n for n in flows if not n['id'].startswith('ku_cloud_')]
    old=next(n for n in flows if n['id']=='59cf4d393c10f90a')
    old['d']=bool(activate and data.get('enabled'))
    destinations=old['wires'][0]
    if 'ku_cloud_influx_format' not in destinations:destinations.append('ku_cloud_influx_format')
    if 'ku_cloud_gps_walk' not in destinations:destinations.append('ku_cloud_gps_walk')
    tab=old['z']
    status=next(n for n in flows if n['id']=='dcbf74bb96b97855')
    status['format']=(ROOT/'integration/node-red/live_status.vue').read_text(encoding='utf-8')
    flows.extend([
        {'id':'ku_cloud_gps_group','type':'ui-group','name':'GPS & Walk','page':'a47ef3e6e3d00b0d','width':'12','height':'3','order':7,'showTitle':True,'className':'','visible':'true','disabled':'false','groupType':'default'},
        {'id':'ku_cloud_gps_walk','type':'ui-template','z':tab,'group':'ku_cloud_gps_group','name':'GPS & walking live','order':1,'width':0,'height':0,'format':(ROOT/'integration/node-red/gps_walk.vue').read_text(encoding='utf-8'),'storeOutMessages':True,'passthru':False,'resendOnRefresh':True,'templateScope':'local','x':660,'y':900,'wires':[[]]},
        {'id':'ku_cloud_tls','type':'tls-config','name':'Verify HiveMQ TLS','cert':'','key':'','ca':'','certname':'','keyname':'','caname':'','verifyservercert':True,'alpnprotocol':'','servername':data.get('host','')},
        {'id':'ku_cloud_broker','type':'mqtt-broker','name':'HiveMQ Cloud KU Watch','broker':data.get('host',''),'port':8883,'clientid':'ku-nodered-local','autoConnect':bool(activate),'usetls':True,'tls':'ku_cloud_tls','protocolVersion':'4','keepalive':'30','cleansession':True,'credentials':{'user':'${KU_MQTT_USER}','password':'${KU_MQTT_PASSWORD}'}},
        {'id':'ku_cloud_input','type':'mqtt in','z':tab,'name':'HiveMQ live','topic':data.get('topic','ku_watch/live'),'qos':'1','datatype':'json','broker':'ku_cloud_broker','d':not bool(activate and data.get('enabled')),'x':390,'y':620,'wires':[destinations.copy()]},
        {'id':'ku_cloud_influx_format','type':'function','z':tab,'name':'KU Watch → InfluxDB iot','func':(ROOT/'integration/node-red/to_influx.js').read_text(encoding='utf-8'),'outputs':1,'noerr':0,'x':680,'y':780,'wires':[['ku_cloud_influx_http']]},
        {'id':'ku_cloud_influx_http','type':'http request','z':tab,'name':'Write real sensor data','method':'POST','ret':'txt','paytoqs':'ignore','url':'','tls':'','persist':False,'proxy':'','insecureHTTPParser':False,'authType':'','senderr':True,'requestTimeout':'5000','x':950,'y':780,'wires':[['ku_cloud_write_status']]},
        {'id':'ku_cloud_write_status','type':'function','z':tab,'name':'DB write status (no secrets)','func':"const ok=msg.statusCode>=200 && msg.statusCode<300; flow.set('ku_influx_retry_after',ok?0:Date.now()+30000); node.status({fill:ok?'green':'red',shape:ok?'dot':'ring',text:'Influx HTTP '+msg.statusCode}); return null;",'outputs':0,'x':1230,'y':780,'wires':[]},
        {'id':'ku_cloud_http_error','type':'catch','z':tab,'name':'DB offline: retry in 30s','scope':['ku_cloud_influx_http'],'uncaught':False,'x':960,'y':840,'wires':[['ku_cloud_write_status']]},
        {'id':'ku_cloud_note','type':'comment','z':tab,'name':'HiveMQ → Node-RED → InfluxDB iot → Grafana','info':'Cloud credentials are loaded locally by settings-ku-watch.js. Only one MQTT input is enabled. No fabricated GPS/BPM; invalid fields are omitted. Watch telemetry has a bounded flash journal, QoS1 and capture-time replay. Broker ACK does not confirm database storage.','x':730,'y':710,'wires':[]}
    ])
    from sync_alert_flow import update as update_alerts
    update_alerts(flows)
    flows_path.write_text(json.dumps(flows,ensure_ascii=False,indent=2),encoding='utf-8')
    # Export references only; no actual passwords or Influx token.
    (ROOT/'integration/node-red/ku-watch-cloud-flow.json').write_text(json.dumps([n for n in flows if n['id'].startswith('ku_cloud_')],ensure_ascii=False,indent=2),encoding='utf-8')
    settings=f'''// KU Watch local environment; keep passwords out of exported flows.
const fs=require('fs');
const settings=require('./settings.js');
const local=JSON.parse(fs.readFileSync({json.dumps(str(LOCAL))},'utf8'));
process.env.KU_MQTT_USER=local.reader_user||'';
process.env.KU_MQTT_PASSWORD=local.reader_password||'';
process.env.KU_INFLUX_URL='http://127.0.0.1:8181';
process.env.KU_INFLUX_DATABASE='iot';
const source=fs.readFileSync({json.dumps(str(ROOT/'include/config.h'))},'utf8');
const token=source.match(/INFLUX_TOKEN\\[\\]\\s*=\\s*"([^"\\n]+)"/);
process.env.KU_INFLUX_TOKEN=token?token[1]:'';
settings.uiHost='127.0.0.1';
module.exports=settings;
'''
    (userdir/'settings-ku-watch.js').write_text(settings,encoding='utf-8')
    return backup

def gui():
    app=tk.Tk();app.title('KU Watch • เชื่อม HiveMQ Cloud');app.geometry('720x475')
    box=ttk.Frame(app,padding=24);box.pack(fill='both',expand=True)
    ttk.Label(box,text='ตั้งค่า HiveMQ Cloud',font=('Leelawadee UI',20,'bold')).grid(row=0,columnspan=2,sticky='w',pady=(0,8))
    ttk.Label(box,text='กรอกบัญชี MQTT ที่สร้างใน Access Management\nรหัสผ่านเก็บในเครื่องนี้ ไม่ต้องส่งในแชต').grid(row=1,columnspan=2,sticky='w',pady=(0,16))
    existing=json.loads(LOCAL.read_text(encoding='utf-8')) if LOCAL.exists() else {}
    values={}
    fields=[('host','เซิร์ฟเวอร์',HOST),('watch_user','ชื่อผู้ใช้บอร์ด (Publish Only)','ku-watch'),('watch_password','รหัสผ่านบอร์ด',''),('reader_user','ชื่อผู้ใช้ Node-RED (Subscribe Only)','ku-nodered'),('reader_password','รหัสผ่าน Node-RED','')]
    for row,(key,label,default) in enumerate(fields,2):
        ttk.Label(box,text=label).grid(row=row,column=0,sticky='w',pady=8)
        value=tk.StringVar(value=existing.get(key,default));values[key]=value
        ttk.Entry(box,textvariable=value,width=48,show='●' if 'password' in key else '').grid(row=row,column=1,sticky='ew',padx=(15,0))
    status=tk.StringVar(value='บันทึกแล้วให้กลับมาบอกในแชต เพื่อทดสอบและอัปโหลดบอร์ด')
    def save():
        try:
            data=validate({key:val.get() for key,val in values.items()});prepare(data)
        except Exception as exc:messagebox.showerror('ยังบันทึกไม่ได้',str(exc));return
        status.set('บันทึกแล้ว ✓ กลับไปบอกว่า “กรอกแล้ว” ได้เลยครับ')
    ttk.Button(box,text='บันทึกการเชื่อมต่อ',command=save).grid(row=8,columnspan=2,sticky='e',pady=22)
    ttk.Label(box,textvariable=status).grid(row=9,columnspan=2,sticky='w')
    app.mainloop()

if __name__=='__main__':
    if '--activate' in sys.argv:
        data=json.loads(LOCAL.read_text(encoding='utf-8'))
        if data.get('enabled'):
            check=subprocess.run(['C:/Program Files/nodejs/node.exe',str(ROOT/'tools/test_cloud_connection.cjs'),'--auth-only'])
            if check.returncode:sys.exit(check.returncode)
        prepare(data,activate=bool(data.get('enabled')))
        print('Node-RED connection prepared. Start or restart Node-RED to use it.')
    else:gui()
