"""Download KU Watch activity files over USB and create standard TCX v2 files."""
from __future__ import annotations
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import queue
import struct
import sys
import threading
import time
import webbrowser
import xml.etree.ElementTree as ET
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent/'vendor'))
NS = 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2'
ET.register_namespace('', NS)
HEADER = struct.Struct('<8sIIQII')
RECORD = struct.Struct('<IiiiHHIII')
GPS, HEART, ALTITUDE, STOP = 1, 2, 4, 0x8000

def decode(raw: bytes):
    if len(raw) < 32:
        raise ValueError('Activity header is incomplete')
    magic, version, size, utc, period, crc = HEADER.unpack_from(raw)
    if magic != b'KUWALK1\0' or version != 1 or size != 32 or period != 1000:
        raise ValueError('Unsupported activity format')
    if zlib.crc32(raw[:28]) != crc or not 1704067200 <= utc <= 4102444799:
        raise ValueError('Activity header checksum or time is invalid')
    records, stopped, previous, last_distance = [], False, -1, 0
    for offset in range(32, len(raw) - 31, 32):
        block = raw[offset:offset+32]
        ms, lat, lon, alt, bpm, flags, distance, reserved, checksum = RECORD.unpack(block)
        if zlib.crc32(block[:28]) != checksum:
            raise ValueError(f'Activity record checksum failed at byte {offset}')
        if stopped or flags & ~(GPS | HEART | ALTITUDE | STOP) or reserved:
            raise ValueError('Invalid activity record flags')
        if ms < previous or (ms == previous and not flags & STOP) or ms > 86400000:
            raise ValueError('Activity times are out of order')
        if distance < last_distance:
            raise ValueError('Activity distance went backwards')
        if flags & GPS and (abs(lat) > 900000000 or abs(lon) > 1800000000):
            raise ValueError('Invalid GPS coordinates')
        if flags & HEART and not 300 <= bpm <= 2200:
            raise ValueError('Invalid heart rate')
        if flags & ALTITUDE and not flags & GPS:
            raise ValueError('Altitude without a valid position')
        if flags & STOP:
            if flags != STOP:
                raise ValueError('Invalid stop marker')
            stopped = True
        else:
            records.append(dict(ms=ms, lat=lat, lon=lon, alt=alt, bpm=bpm, flags=flags, distance=distance))
        previous, last_distance = ms, distance
    if stopped and len(raw) % 32:
        raise ValueError('Unexpected data after the stop marker')
    if len(records) < 2 or previous <= 0:
        raise ValueError('Activity is too short: record for at least two seconds')
    return dict(utc=utc, duration_ms=previous, distance_cm=last_distance, records=records,
                recovered=not stopped, partial_bytes=len(raw) % 32)

def tcx_bytes(activity):
    def tag(name): return f'{{{NS}}}{name}'
    def child(parent, name, text=None, **attrs):
        e = ET.SubElement(parent, tag(name), attrs)
        if text is not None: e.text = str(text)
        return e
    start = dt.datetime.fromtimestamp(activity['utc'], dt.timezone.utc)
    def iso(ms=0): return (start + dt.timedelta(milliseconds=ms)).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
    root = ET.Element(tag('TrainingCenterDatabase'))
    activities = child(root, 'Activities')
    # The official TCX schema allows Running/Biking/Other; select Walk in Strava after import.
    act = child(activities, 'Activity', Sport='Other')
    child(act, 'Id', iso())
    lap = child(act, 'Lap', StartTime=iso())
    child(lap, 'TotalTimeSeconds', f"{activity['duration_ms']/1000:.3f}")
    child(lap, 'DistanceMeters', f"{activity['distance_cm']/100:.2f}")
    child(lap, 'Calories', '0')
    child(lap, 'Intensity', 'Active')
    child(lap, 'TriggerMethod', 'Manual')
    track, previous_ms, previous_gps = None, None, None
    for r in activity['records']:
        has_gps = bool(r['flags'] & GPS)
        if track is None or has_gps != previous_gps or r['ms']-previous_ms > 5000:
            track = child(lap, 'Track')
        point = child(track, 'Trackpoint')
        child(point, 'Time', iso(r['ms']))
        if has_gps:
            pos = child(point, 'Position')
            child(pos, 'LatitudeDegrees', f"{r['lat']/1e7:.7f}")
            child(pos, 'LongitudeDegrees', f"{r['lon']/1e7:.7f}")
        if r['flags'] & ALTITUDE: child(point, 'AltitudeMeters', f"{r['alt']/100:.2f}")
        child(point, 'DistanceMeters', f"{r['distance']/100:.2f}")
        if r['flags'] & HEART:
            heart = child(point, 'HeartRateBpm')
            child(heart, 'Value', (r['bpm'] + 5)//10)
        previous_ms, previous_gps = r['ms'], has_gps
    notes = 'KU Watch walking activity. Calories were not measured. Missing GPS/heart-rate values were omitted.'
    if activity['recovered']: notes += ' Recovered after an interrupted recording; the final seconds may be missing.'
    child(act, 'Notes', notes)
    ET.indent(root, space='  ')
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)

class Watch:
    def __init__(self, port=None):
        import serial
        from serial.tools import list_ports
        if not port:
            candidates = [p.device for p in list_ports.comports() if p.vid == 0x303a and p.pid == 0x1001]
            if len(candidates) != 1: raise RuntimeError('เลือกพอร์ต Super Mini ให้ชัดเจน หรือเสียบเพียงบอร์ดเดียว')
            port = candidates[0]
        self.serial = serial.Serial(port=None, baudrate=115200, timeout=.2, write_timeout=5)
        self.serial.dtr = self.serial.rts = False
        self.serial.port = port
        self.serial.open()
        self.port = port
        self.pending = bytearray()
    def close(self): self.serial.close()
    def send(self, command): self.serial.write((command+'\n').encode('ascii'))
    def lines(self, timeout=15):
        deadline = time.monotonic()+timeout
        while time.monotonic() < deadline:
            self.pending.extend(self.serial.read(self.serial.in_waiting or 1))
            if len(self.pending)>16384: raise RuntimeError('USB response exceeded line buffer')
            while b'\n' in self.pending:
                raw, _, rest = self.pending.partition(b'\n'); self.pending[:] = rest
                line = raw.decode('ascii', errors='replace').strip()
                if line.startswith('REC ERROR'): raise RuntimeError(line)
                if line: yield line
        raise TimeoutError('บอร์ดไม่ตอบ ตรวจสาย USB และปิด Serial Monitor อื่นก่อน')
    def status(self):
        self.send('RECSTATUS')
        for line in self.lines():
            if line.startswith('REC STATUS '):
                result = {}
                body, _, message = line[11:].partition(' message=')
                for item in body.split():
                    k, v = item.split('=',1); result[k] = int(v)
                result['message'] = message
                return result
    def set_time(self):
        self.send('TIME '+str(int(time.time())))
        for line in self.lines():
            if line == 'TIME OK': return
    def list(self):
        self.send('RECLIST'); found = []; begun=False
        for line in self.lines():
            if line == 'REC LIST BEGIN': begun=True
            elif begun and line.startswith('REC FILE '):
                _, _, identity, size = line.split(); found.append((int(identity), int(size)))
            elif begun and line == 'REC LIST END': return sorted(found)
    def download(self, identity):
        self.send(f'RECGET {identity}'); result=bytearray(); size=None
        deadline=time.monotonic()+240
        while time.monotonic()<deadline:
            for line in self.lines(timeout=20):
                if line.startswith('REC BEGIN '):
                    _, _, got, count = line.split()
                    if int(got)!=identity or not 32<=int(count)<=1048576: raise ValueError('Invalid download header')
                    size=int(count)
                elif line.startswith('REC DATA '):
                    _, _, got, offset, data = line.split()
                    if size is None or int(got)!=identity or int(offset)!=len(result): raise ValueError('USB transfer lost a block')
                    result.extend(bytes.fromhex(data))
                    if len(result)>size: raise ValueError('USB transfer is larger than expected')
                    break
                elif line.startswith('REC END '):
                    _, _, got, count, crc = line.split()
                    if int(got)!=identity or int(count)!=len(result) or len(result)!=size or zlib.crc32(result)!=int(crc,16):
                        raise ValueError('USB transfer checksum failed; download again')
                    return bytes(result)
        raise TimeoutError('Activity download took too long')

def save_activity(raw, identity, output):
    activity=decode(raw)
    stamp=dt.datetime.fromtimestamp(activity['utc'],dt.timezone.utc).strftime('%Y%m%d_%H%M%S_UTC')
    base=Path(output)/f'KU_Walk_{stamp}_{identity:06d}'
    base.parent.mkdir(parents=True,exist_ok=True)
    # Preserve existing exports if a file with the same name has different content.
    raw_path=base.with_suffix('.kua')
    if raw_path.exists() and raw_path.read_bytes()!=raw: raise FileExistsError(f'Different file already exists: {raw_path}')
    raw_path.write_bytes(raw)
    tcx=base.with_suffix('.tcx'); tcx.write_bytes(tcx_bytes(activity))
    summary={k:v for k,v in activity.items() if k!='records'}
    summary.update(samples=len(activity['records']),gps_samples=sum(bool(r['flags']&GPS) for r in activity['records']),
                   heart_samples=sum(bool(r['flags']&HEART) for r in activity['records']))
    base.with_suffix('.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    return tcx,summary

def gui():
    import tkinter as tk
    from tkinter import ttk, messagebox
    root=tk.Tk(); root.title('KU Watch → Strava'); root.geometry('710x570')
    events=queue.Queue(); busy=False
    port=tk.StringVar(value='COM15'); status=tk.StringVar(value='เสียบ Super Mini แล้วกดเชื่อมต่อ / ตั้งเวลา')
    ttk.Label(root,text='บันทึกการเดิน → ไฟล์สำหรับ Strava',font=('Tahoma',17,'bold')).pack(pady=16)
    top=ttk.Frame(root); top.pack(fill='x',padx=20)
    ttk.Label(top,text='COM15 หรือ http://IP ของนาฬิกา').pack(side='left')
    ttk.Entry(top,textvariable=port,width=27).pack(side='left',padx=10)
    wifi_password=tk.StringVar();credentials=ttk.Frame(root);credentials.pack(fill='x',padx=20,pady=5)
    ttk.Label(credentials,text='รหัสตั้งค่า (ใช้เมื่อเชื่อม Wi-Fi)').pack(side='left')
    ttk.Entry(credentials,textvariable=wifi_password,show='*',width=22).pack(side='left',padx=10)
    ttk.Label(root,textvariable=status,wraplength=660).pack(padx=20,pady=12)
    table=ttk.Treeview(root,columns=('id','size'),show='headings',height=9,selectmode='browse')
    table.heading('id',text='หมายเลขกิจกรรม'); table.heading('size',text='ขนาด (ไบต์)'); table.pack(fill='x',padx=20)
    ttk.Label(root,text='ที่นาฬิกา: ไปหน้า WALK แล้วกดค้างเพื่อเริ่ม / หยุด\nไฟล์ถูกเก็บในเครื่องคอม การส่งเข้า Strava ทำหลังจากเลือกไฟล์ด้วยตัวเอง',justify='center').pack(pady=12)
    buttons=[]
    def work(action):
        nonlocal busy
        if busy:return
        selected=table.selection()
        identity=int(selected[0]) if selected else None
        if action in ('export','delete') and identity is None:
            messagebox.showinfo('เลือกกิจกรรม','เลือกกิจกรรมในตารางก่อน');return
        if action=='delete' and not messagebox.askyesno('ลบจากนาฬิกา',f'ลบกิจกรรม {identity} จากนาฬิกา? ควรดึงไฟล์เก็บไว้ก่อน'):
            return
        selected_port=port.get().strip();selected_password=wifi_password.get();busy=True
        for b in buttons:b.state(['disabled'])
        status.set('กำลังทำงานกับนาฬิกา…')
        def run():
            watch=None
            try:
                if selected_port.startswith('http://'):
                    from activity_export_wifi import WifiWatch
                    watch=WifiWatch(selected_port,selected_password)
                else:watch=Watch(selected_port or None)
                st=watch.status()
                if action=='connect':
                    watch.set_time(); text='ตั้งเวลาสำเร็จ พร้อมเริ่มเดินจากหน้า WALK'
                elif action=='export':
                    if st['active']:raise RuntimeError('ยังบันทึกอยู่ ให้กดค้างที่หน้า WALK เพื่อหยุดก่อน')
                    path,summary=save_activity(watch.download(identity),identity,ROOT/'activities')
                    text=f"ได้ไฟล์ {path.name} | พิกัด {summary['gps_samples']} จุด / ชีพจร {summary['heart_samples']} จุด"
                    if summary['recovered']:text+=' | กู้คืนจากการปิดเครื่องระหว่างบันทึก'
                elif action=='delete':
                    watch.send(f'RECDELETE {identity}')
                    for line in watch.lines():
                        if line==f'REC DELETED {identity}':break
                    text=f'ลบกิจกรรม {identity} จากนาฬิกาแล้ว'
                else:text='อัปเดตรายการแล้ว'
                rows=watch.list();st=watch.status()
                text+=f" | ว่าง {st['free']//1024} KB"
                if st['active']:text+=' | กำลังบันทึก'
                events.put(('ok',text,rows))
            except Exception as exc:events.put(('error',str(exc),None))
            finally:
                if watch:watch.close()
        threading.Thread(target=run,daemon=True).start()
    row=ttk.Frame(root);row.pack(pady=5)
    for label,action in [('เชื่อมต่อ / ตั้งเวลา','connect'),('อ่านรายการ','list'),('ดึงไฟล์ TCX','export'),('ลบจากนาฬิกา','delete')]:
        b=ttk.Button(row,text=label,command=lambda a=action:work(a));b.pack(side='left',padx=4);buttons.append(b)
    row2=ttk.Frame(root);row2.pack(pady=10)
    def folder():
        p=ROOT/'activities';p.mkdir(exist_ok=True);os.startfile(p)
    ttk.Button(row2,text='เปิดโฟลเดอร์ไฟล์',command=folder).pack(side='left',padx=8)
    ttk.Button(row2,text='เปิดหน้านำเข้า Strava',command=lambda:webbrowser.open('https://www.strava.com/upload/select')).pack(side='left',padx=8)
    def poll():
        nonlocal busy
        try:
            while True:
                kind,text,rows=events.get_nowait();busy=False
                for b in buttons:b.state(['!disabled'])
                status.set(text)
                if kind=='error':messagebox.showerror('ยังทำรายการไม่สำเร็จ',text)
                elif rows is not None:
                    for item in table.get_children():table.delete(item)
                    for identity,size in rows:table.insert('',tk.END,iid=str(identity),values=(identity,size))
        except queue.Empty:pass
        root.after(150,poll)
    root.after(150,poll);root.mainloop()

def main():
    p=argparse.ArgumentParser();p.add_argument('--gui',action='store_true');p.add_argument('--port')
    p.add_argument('--list',action='store_true');p.add_argument('--export',help='ID, latest, or all')
    p.add_argument('--output',type=Path,default=ROOT/'activities');p.add_argument('--set-time',action='store_true')
    p.add_argument('--convert',type=Path,help='Convert an already downloaded .kua file')
    a=p.parse_args()
    if a.gui or not any((a.list,a.export,a.set_time,a.convert)):return gui()
    if a.convert:
        result,summary=save_activity(a.convert.read_bytes(),0,a.output);print(result);print(json.dumps(summary));return
    watch=Watch(a.port)
    try:
        status=watch.status();print(json.dumps(status))
        if a.set_time:watch.set_time();print('TIME OK')
        rows=watch.list()
        if a.list:print(json.dumps(rows))
        if a.export:
            if status['active']:raise RuntimeError('Stop recording before exporting')
            ids=[i for i,_ in rows]
            chosen=ids if a.export=='all' else ([max(ids)] if a.export=='latest' and ids else [] if a.export=='latest' else [int(a.export)])
            if not chosen:raise RuntimeError('No activities recorded yet')
            for identity in chosen:
                path,summary=save_activity(watch.download(identity),identity,a.output)
                print(path);print(json.dumps(summary))
    finally:watch.close()

if __name__=='__main__':main()
