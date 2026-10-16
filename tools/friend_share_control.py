"""User-operated start/stop window for a scoped, temporary Grafana viewing link."""
from pathlib import Path
import hashlib
import json
import os
import queue
import re
import sqlite3
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
import urllib.request
import webbrowser

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/friend_share'
CONFIG=ROOT/'config/friend-share.local.json'
DB=Path('D:/iot2026/Grafana/grafana/data/grafana.db')
children=[]
process_lock=threading.RLock()
stop_event=threading.Event()
events=queue.Queue()

def stop():
    with process_lock:
        stop_event.set()
        CONFIG.write_text(json.dumps({'enabled':False}),encoding='utf-8')
        for child in children:
            if child.poll() is None:child.terminate()
        children.clear()

def start():
    try:
        con=sqlite3.connect('file:'+DB.as_posix()+'?mode=ro',uri=True)
        row=con.execute("SELECT access_token,is_enabled FROM dashboard_public WHERE dashboard_uid=? AND org_id=1",('ku-watch-friends',)).fetchone()
        con.close()
        if not row or not row[1]:raise RuntimeError('ยังไม่ได้เปิด Share externally ของ KU Watch • Friends View ใน Grafana')
        access=row[0]
        if not re.fullmatch(r'[a-fA-F0-9]{32}',access):raise RuntimeError('รูปแบบลิงก์แชร์ไม่ถูกต้อง')
        # Verify the external-view route without Grafana cookies or administrator credentials.
        with urllib.request.urlopen('http://127.0.0.1:3000/api/public/dashboards/'+access,timeout=10) as r:
            public=json.load(r)
        if public.get('dashboard',{}).get('uid')!='ku-watch-friends':raise RuntimeError('กราฟที่แชร์ไม่ตรงกับหน้าสำหรับเพื่อน')
        exe=OUT/'cloudflared.exe'
        manifest=json.loads((OUT/'cloudflared-download.json').read_text())
        if hashlib.sha256(exe.read_bytes()).hexdigest()!=manifest['sha256']:
            raise RuntimeError('ไฟล์เชื่อมต่อถูกเปลี่ยนแปลง กรุณาตรวจใหม่')
        flags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
        with process_lock:
            if stop_event.is_set():return
            CONFIG.write_text(json.dumps({'enabled':True,'access_token':access}),encoding='utf-8')
            with (OUT/'gateway.log').open('w') as log:
                children.append(subprocess.Popen([sys.executable,str(ROOT/'tools/friend_share_gateway.py')],cwd=ROOT,
                    stdout=log,stderr=log,creationflags=flags))
        # Wait for our gateway, checking that it serves the intended public dashboard.
        for _ in range(30):
            if stop_event.is_set():return
            try:
                with urllib.request.urlopen('http://127.0.0.1:8767/api/public/dashboards/'+access,timeout=1) as r:
                    result=json.load(r)
                if result.get('dashboard',{}).get('uid')=='ku-watch-friends':break
            except Exception:time.sleep(.2)
        else:raise RuntimeError('เปิดหน้าดูกราฟในเครื่องไม่สำเร็จ')
        logpath=OUT/'tunnel.log'
        with process_lock:
            if stop_event.is_set():return
            with logpath.open('w') as log:
                tunnel=subprocess.Popen([str(exe),'tunnel','--url','http://127.0.0.1:8767',
                    '--no-autoupdate','--protocol','http2'],cwd=ROOT,stdout=log,stderr=log,creationflags=flags)
                children.append(tunnel)
        for _ in range(120):
            if stop_event.is_set():return
            match=re.search(r'https://[a-z0-9-]+\.trycloudflare\.com',logpath.read_text(errors='replace'))
            if match:
                link=match[0]+'/public-dashboards/'+access
                (OUT/'link.txt').write_text(link,encoding='utf-8')
                events.put(('link',link));return
            if tunnel.poll() is not None:raise RuntimeError('โปรแกรมเชื่อมต่อหยุดทำงาน โปรดแจ้งกลับในแชต')
            time.sleep(.5)
        raise RuntimeError('ยังเชื่อมอินเทอร์เน็ตไม่ได้ภายใน 60 วินาที')
    except Exception as exc:
        stop();events.put(('error',str(exc)))

def main():
    OUT.mkdir(exist_ok=True,parents=True)
    app=tk.Tk();app.title('KU Watch • ลิงก์ให้เพื่อนดู');app.geometry('730x440')
    frame=ttk.Frame(app,padding=24);frame.pack(fill='both',expand=True)
    ttk.Label(frame,text='แชร์กราฟให้เพื่อนดู',font=('Leelawadee UI',20,'bold')).pack(anchor='w')
    ttk.Label(frame,text='เพื่อนเปิดดูผ่านลิงก์ได้อย่างเดียว แก้ไขข้อมูลไม่ได้\nผู้ที่ได้รับลิงก์ต่อสามารถดูได้ รวมชีพจรและพิกัด GPS เมื่ออ่านได้\nใช้ Cloudflare ส่งต่อหน้าเว็บ • ปิดหน้าต่างนี้เพื่อหยุดแชร์\nลิงก์ชั่วคราวจะเปลี่ยนเมื่อเปิดใหม่',wraplength=675).pack(anchor='w',pady=12)
    consent=tk.BooleanVar()
    ttk.Checkbutton(frame,text='ยืนยันแชร์ข้อมูลในกราฟ และยอมรับเงื่อนไขบริการ Cloudflare',variable=consent).pack(anchor='w')
    ttk.Button(frame,text='อ่านเงื่อนไข Cloudflare',command=lambda:webbrowser.open('https://www.cloudflare.com/terms/')).pack(anchor='w',pady=5)
    status=tk.StringVar(value='เปิด Share externally ของหน้า Friends View ก่อน แล้วกดเปิดลิงก์')
    link=tk.StringVar()
    ttk.Label(frame,textvariable=status,wraplength=670).pack(anchor='w',pady=10)
    entry=ttk.Entry(frame,textvariable=link,state='readonly');entry.pack(fill='x',pady=6)
    def begin():
        if not consent.get():return messagebox.showinfo('ยืนยันการแชร์','กรุณาติ๊กยืนยันการแชร์และเงื่อนไขก่อนครับ')
        stop_event.clear();start_button.state(['disabled']);status.set('กำลังเปิดลิงก์…');link.set('')
        threading.Thread(target=start,daemon=True).start()
    buttons=ttk.Frame(frame);buttons.pack(fill='x',pady=8)
    start_button=ttk.Button(buttons,text='เปิดลิงก์ให้เพื่อนดู',command=begin);start_button.pack(side='left')
    def copy():
        if link.get():app.clipboard_clear();app.clipboard_append(link.get());status.set('คัดลอกแล้ว ส่งลิงก์นี้ให้เพื่อนได้เลย')
    ttk.Button(buttons,text='คัดลอกลิงก์',command=copy).pack(side='left',padx=8)
    def halt():stop();link.set('');status.set('หยุดแชร์แล้ว');start_button.state(['!disabled'])
    ttk.Button(buttons,text='หยุดแชร์',command=halt).pack(side='right')
    def poll():
        while not events.empty():
            kind,value=events.get()
            if kind=='link':link.set(value);status.set('ได้ลิงก์แล้ว กำลังรอเครือข่ายพร้อม เปิดหน้าต่างนี้ค้างไว้')
            else:status.set(value);start_button.state(['!disabled'])
        app.after(250,poll)
    def close():stop();app.destroy()
    app.protocol('WM_DELETE_WINDOW',close);poll();app.mainloop()

if __name__=='__main__':main()
