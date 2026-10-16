"""User-authorized local admin password reset and KU Watch dashboard activation.
The new password exists only in memory and is passed to Grafana CLI over stdin.
"""
from pathlib import Path
import base64
import datetime
import json
import queue
import re
import sqlite3
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
GRAFANA=Path('D:/iot2026/Grafana/grafana')

def reset_and_setup(password):
    database=GRAFANA/'data/grafana.db'
    backup=GRAFANA/'data/ku-watch-backups'/('before-reset-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'.db')
    backup.parent.mkdir(exist_ok=True)
    with sqlite3.connect(database.as_uri()+'?mode=ro',uri=True) as source,sqlite3.connect(backup) as dest:
        source.backup(dest)
    result=subprocess.run([str(GRAFANA/'bin/grafana.exe'),'cli','--homepath',str(GRAFANA),
        'admin','reset-admin-password','--user-id','1','--password-from-stdin'],input=password+'\n',
        text=True,capture_output=True,timeout=45,cwd=GRAFANA,creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:raise RuntimeError('Grafana รีเซ็ตไม่สำเร็จ ตรวจสิทธิ์เข้าถึงไฟล์ฐานข้อมูล')
    auth='Basic '+base64.b64encode(('admin:'+password).encode()).decode()
    def request(route,data=None,method=None):
        req=urllib.request.Request('http://127.0.0.1:3000'+route,
            data=json.dumps(data).encode() if data is not None else None,
            headers={'Authorization':auth,'Content-Type':'application/json'},method=method)
        with urllib.request.urlopen(req,timeout=20) as r:return json.load(r)
    profile=request('/api/user')
    if profile.get('login')!='admin':raise RuntimeError('ล็อกอินไม่ตรงบัญชี admin')
    request('/api/admin/provisioning/dashboards/reload',{},'POST')
    dashboard=request('/api/dashboards/uid/ku-watch-live')
    # Keep the existing data source and use the Influx token already validated locally.
    datasource=request('/api/datasources/uid/efwpjfdzlacqoc')
    config=(ROOT/'include/config.h').read_text(encoding='utf-8')
    token=re.search(r'INFLUX_TOKEN\[\]\s*=\s*"([^"\n]+)"',config).group(1)
    datasource['secureJsonData']={'token':token}
    request('/api/datasources/uid/efwpjfdzlacqoc',datasource,'PUT')
    query={'refId':'A','datasource':{'type':'influxdb','uid':'efwpjfdzlacqoc'},
        'rawSql':'SELECT * FROM "ku_watch" WHERE $__timeFilter(time) ORDER BY time ASC',
        'rawQuery':True,'editorMode':'code','format':'table','intervalMs':1000,'maxDataPoints':1000}
    response=request('/api/ds/query',{'from':'now-15m','to':'now','queries':[query]},'POST')
    res=response.get('results',{}).get('A',{})
    validation={'password_reset':True,'admin_login':True,'dashboard_uid':dashboard['dashboard']['uid'],
        'query_status':res.get('status'),'frames':len(res.get('frames',[])),
        'query_error':res.get('error')}
    (ROOT/'output/grafana_setup_validation.json').write_text(json.dumps(validation,indent=2),encoding='utf-8')
    if res.get('error'):return 'เปลี่ยนรหัสและเพิ่มกราฟแล้ว แต่กราฟยังอ่านฐานข้อมูลไม่ได้ ให้กลับไปแจ้งในแชต'
    return 'เปลี่ยนรหัสแล้ว ✓ ใช้ admin + รหัสใหม่ล็อกอิน Grafana ได้\nกราฟ KU Watch พร้อมและทดสอบอ่านข้อมูลสำเร็จ'

def main():
    app=tk.Tk();app.title('Grafana • ตั้งรหัสใหม่');app.geometry('600x365')
    box=ttk.Frame(app,padding=25);box.pack(fill='both',expand=True)
    ttk.Label(box,text='ตั้งรหัสใหม่สำหรับ Grafana',font=('Leelawadee UI',19,'bold')).pack(anchor='w')
    ttk.Label(box,text='บัญชีเดิม: admin\nข้อมูลและการตั้งค่าคงเดิม • รหัสใหม่ไม่ถูกบันทึกลงไฟล์').pack(anchor='w',pady=12)
    entries=[]
    for label in ['รหัสใหม่ (อย่างน้อย 8 ตัวอักษร)','ยืนยันรหัสใหม่']:
        ttk.Label(box,text=label).pack(anchor='w')
        e=ttk.Entry(box,show='●',width=60);e.pack(fill='x',pady=(2,10));entries.append(e)
    events=queue.Queue();status=tk.StringVar()
    def submit():
        password=entries[0].get()
        if len(password)<8 or '\n' in password or password!=entries[1].get():
            messagebox.showerror('ตรวจรหัสอีกครั้ง','รหัสต้องตรงกันและมีอย่างน้อย 8 ตัวอักษร');return
        button.state(['disabled']);status.set('กำลังเปลี่ยนรหัสและตรวจกราฟ…')
        def run():
            try:events.put((True,reset_and_setup(password)))
            except Exception as exc:events.put((False,'ดำเนินการไม่ครบ: '+str(exc)))
        threading.Thread(target=run,daemon=True).start()
    button=ttk.Button(box,text='เปลี่ยนรหัส admin และเปิดกราฟ KU Watch',command=submit);button.pack(anchor='e',pady=8)
    ttk.Label(box,textvariable=status,wraplength=550).pack(anchor='w',pady=4)
    def poll():
        try:
            ok,text=events.get_nowait();status.set(text)
            for e in entries:e.delete(0,'end')
            if not ok:button.state(['!disabled'])
        except queue.Empty:pass
        app.after(200,poll)
    app.after(200,poll);app.mainloop()

if __name__=='__main__':main()
