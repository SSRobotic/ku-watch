"""Publish only actual project media, preserving raw files and dated captions."""
from pathlib import Path
import hashlib,json,shutil,zipfile,html,importlib.util
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[1]
B=ROOT/'output/ppt_academic_20261016/build'
OUT=ROOT/'output/ppt_academic_20261016/deliverable'
PUBLIC=OUT/'KU_Watch_ภาพและคลิป'
PUBLIC.mkdir(parents=True,exist_ok=True)
entries=[]
def add(source,folder,title,scope,date):
    source=Path(source)
    if not source.is_absolute():source=ROOT/source
    dest=PUBLIC/folder/source.name;dest.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(source,dest)
    entries.append(dict(file=dest.relative_to(PUBLIC).as_posix(),title=title,scope=scope,date=date,sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),bytes=dest.stat().st_size))

capture=json.loads((B/'dashboard_verified/manifest.json').read_text('utf8'))
assert capture['status']=='completed' and len(capture['panels'])==77
for panel in capture['panels']:
    add(B/'dashboard_verified'/panel['file'],'01_Grafana_16Oct',panel['title'],'ภาพเต็มแผงข้อมูล ช่วงเลือก 14:00–17:00 น.','16 ต.ค. 2569')
backend=json.loads((B/'backend/manifest.json').read_text('utf8'))
for group in backend['dashboard_groups']:
    if group['title'].split('\n')[0]=='Watch Preview':continue
    add(B/'backend'/group['file'],'02_NodeRED_16Oct',group['title'].split('\n')[0],'ภาพครบกลุ่มข้อมูลจริง','16 ต.ค. 2569')
for name,title,scope in [('NodeRED_flow_fit.png','Node-RED flow','ซูมมุมมองให้เห็นโหนดครบ ไม่เปลี่ยน flow'),('WatchPreview_original.jpg','ภาพต้นฉบับ Watch Preview','ภาพที่บันทึกไว้ ไม่ใช่การถ่ายทอดจอสด'),('Influx_counts.png','InfluxDB: จำนวนข้อมูล','ผลตอบกลับ SQL จริงผ่าน browser pretty-print'),('Influx_rows.png','InfluxDB: ตัวอย่างข้อมูล','ผลตอบกลับ SQL จริงผ่าน browser pretty-print')]:
    add(B/'backend'/name,'03_Backend_16Oct',title,scope,'16 ต.ค. 2569' if name!='WatchPreview_original.jpg' else 'ภาพบันทึกเดิม')
inventory=json.loads((B/'media_inventory.json').read_text('utf8'))
for item in inventory['photos']:
    add(item['display_file'],'04_ภาพตัวเครื่อง',Path(item['source']).name,'ภาพผู้ใช้ส่งมา ปรับการวางแนวตาม EXIF โดยไม่ตัดขอบ','ภาพจากผู้ใช้')
for item in inventory['videos']:
    add(item['source'],'05_คลิปผู้ใช้',Path(item['source']).name,'คลิปต้นฉบับของผู้ใช้ครบความยาว; คลิปชื่อไจโรเป็นการสาธิตความเร่ง/การเคลื่อนไหวของ GY-51','คลิปจากผู้ใช้')
for src,title in [('output/slide_media_actual_20261016/คลิปวันนี้/Grafana_สด_16ตุลา2569_60วินาที.mp4','Grafana: ข้อมูลไหลจริง 60 วินาที'),('output/final_acceptance_20261016/recovery_clip_visible/NodeRED_หลังกลับออนไลน์_16ตุลา2569_60วินาที.mp4','Node-RED: หลังกลับออนไลน์ 60 วินาที')]:
    add(src,'06_คลิปแดชบอร์ด',title,'การบันทึกหน้าจอจริง ไม่ใช้แทนผลวัด latency','16 ต.ค. 2569')
for folder,date in [('output/presentation_evidence/slide_evidence_20261014/images','14 ต.ค. 2569'),('output/slide_media_actual_20261016/ภาพวันนี้','16 ต.ค. 2569')]:
    for image in sorted((ROOT/folder).glob('*.png')):
        add(image,'07_ภาพหลักฐานเดิม/'+('14Oct' if '20261014' in folder else '16Oct'),image.stem,'หลักฐานเดิมตามวันที่ บางภาพเป็น viewport เก่า; ภาพครบกลุ่มฉบับใหม่อยู่ด้านบน',date)
csv=ROOT/'output/presentation_media_20261016/current_sd_export/env_1792135219_2f3b6084.csv'
add(csv,'08_CSV_จากMicroSD','CSV จริงจาก MicroSD','61 แถว 26 คอลัมน์ ช่วง 301 วินาที ค่าว่างคงเดิม','16 ต.ค. 2569')
manifest={'created_utc':datetime.now(timezone.utc).isoformat(),'boundary':'Actual project media only. Cumulative MQTT reception is distinct from continuous duration and battery endurance. No synthetic demo data included.','files':entries}
(PUBLIC/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),'utf8')
sections=[]
for item in entries:
    name=item['file'];url=html.escape(name,quote=True);title=html.escape(item['title']);scope=html.escape(item['scope']);date=html.escape(item['date'])
    if name.lower().endswith('.mp4'):media=f'<video src="{url}" controls preload="metadata"></video>'
    elif name.lower().endswith(('.png','.jpg','.jpeg')):media=f'<a href="{url}" target="_blank"><img src="{url}" loading="lazy" alt="{title}"></a>'
    else:media=f'<a class="file" href="{url}">เปิดไฟล์ CSV ต้นฉบับ</a>'
    sections.append(f'<article>{media}<h2>{title}</h2><p>{date} · {scope}</p><a href="{url}" download>เปิด/บันทึกขนาดเต็ม</a></article>')
doc='''<!doctype html><html lang="th"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>KU Watch — ภาพและคลิปประกอบการนำเสนอ</title><style>body{margin:0;background:#eef1f5;color:#223040;font:17px "Leelawadee UI",Tahoma,sans-serif}header{background:#1e3a5f;color:white;padding:40px max(5vw,24px)}header p{max-width:1100px;line-height:1.8}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(400px,1fr));gap:24px;padding:30px}article{padding:18px;background:white;border:1px solid #d5dce4}img,video{width:100%;height:320px;object-fit:contain;background:#182027}h2{font-size:21px;margin:14px 0 8px}p{font-size:15px;line-height:1.7}a{color:#2469a1}.file{display:block;padding:120px 0;text-align:center} @media(max-width:500px){main{display:block}article{margin:0 0 20px}}</style><header><h1>KU Watch — ภาพและคลิปประกอบการนำเสนอ</h1><p>ภาพจริงจาก Grafana ทุกแผง, Node-RED ครบกลุ่ม, ผล SQL จาก InfluxDB, ภาพตัวเครื่อง และคลิปต้นฉบับ คลิกภาพเพื่อดูขนาดเต็ม ภาพเดิมแยกวันที่ไว้ ค่าที่ไม่พร้อมยังแสดงตามระบบจริง</p></header><main>'''+''.join(sections)+'</main></html>'
(PUBLIC/'เปิดดูภาพและคลิป.html').write_text(doc,'utf8')
readme='''KU Watch — ชุดพร้อมนำเสนอ 18 ตุลาคม 2569

1. เปิดไฟล์ .pptx ใน Microsoft PowerPoint บนคอมพิวเตอร์ แล้วกด F5
2. สไลด์หลัก 14 หน้า คลิกวิดีโอเพื่อเล่น มีโน้ตผู้บรรยายและเวลาพูดแนะนำ
3. หน้า 14 มีลิงก์เปิดภาคผนวก 52 หน้า ซึ่งซ่อนไว้จากการกด Next ตามปกติ
4. คลิปฝังในไฟล์ PowerPoint แล้ว ไม่ต้องมีโฟลเดอร์วิดีโอหรืออินเทอร์เน็ตเพื่อเล่นคลิป
5. ภาคผนวกมีปุ่มสารบัญเพื่อย้อนกลับ คลิปเดินฉบับเต็มอยู่ในภาคผนวก
6. ชื่อสมาชิก บทบาท และราคาซื้อเว้นไว้ให้เติมก่อนนำเสนอ
7. ถ้าต้องการเลือกภาพเพิ่มเติม เปิด KU_Watch_ภาพและคลิป/เปิดดูภาพและคลิป.html

ขอบเขตหลักฐาน: รูปและคลิปเก็บจากระบบจริงหรือผู้ใช้ส่งมา ภาพแผงข้อมูลใหม่คงช่วงข้อมูล 16 ต.ค. 2569 เวลา 14:00–17:00 น. รูปเก่ามีวันที่กำกับ ผลรับ MQTT สะสมครบ 24 ชั่วโมงไม่ใช่ผลต่อเนื่อง 24 ชั่วโมงหรืออายุแบตเตอรี่ ข้อที่ยังไม่ตรวจผ่านคงสถานะตามตาราง Requirements
'''
(OUT/'อ่านก่อนนำเสนอ.txt').write_text(readme,'utf8')
(PUBLIC/'อ่านก่อนใช้สื่อ.txt').write_text(readme,'utf8')
# Fail closed on known configured credentials without printing any secret value.
spec=importlib.util.spec_from_file_location('delivery',ROOT/'tools/package_delivery.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
secrets=module.known_secrets()
for file in PUBLIC.rglob('*'):
    if file.is_file():
        data=file.read_bytes()
        if any(secret in data for secret in secrets):raise RuntimeError('Known credential found in public media: '+file.name)
target=OUT/'KU_Watch_ภาพและคลิปครบชุด.zip'
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
    for file in sorted(PUBLIC.rglob('*')):
        if file.is_file():archive.write(file,file.relative_to(OUT).as_posix())
with zipfile.ZipFile(target) as archive:assert archive.testzip() is None
report={'images':sum(x['file'].lower().endswith(('.png','.jpg','.jpeg')) for x in entries),'videos':sum(x['file'].endswith('.mp4') for x in entries),'files':len(entries),'archive':str(target),'bytes':target.stat().st_size,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'known_secret_scan_passed':True}
(B/'gallery_package_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8');print(json.dumps(report,ensure_ascii=False))
