"""Patch the retained checklist in place; keep original criteria and other parts unchanged."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
from zipfile import ZipFile
from copy import deepcopy
import hashlib,json,re
from lxml import etree as E
ROOT=Path(__file__).resolve().parents[1];A=ROOT/'output/final_acceptance_20261016';OUT=ROOT/'output/final_delivery_20261016';OUT.mkdir(exist_ok=True)
SRC=ROOT/'output/deadline_20261018/requirements_accepted_20261014/KU_Watch_ตารางเช็กRequirements_ตรวจรับล่าสุด_14ตุลาคม2569.docx'
EXPECTED='ddb18d497c1688b5376719e973a356d11713c644efae6fc301f8359b51d94d07'
assert hashlib.sha256(SRC.read_bytes()).hexdigest()==EXPECTED
def read(p,default=None):return json.loads(p.read_text(encoding='utf-8-sig')) if p.exists() else default
mqtt=read(A/'mqtt_5min_canonical.json',{});outage=read(A/'offline_10min/result.json',{});nvs=read(A/'nvs_reboot.json',{});sensors=read(A/'sensors_finger_stable_65s.json',read(A/'sensors_finger_65s.json',read(A/'sensors_65s_after.json',read(A/'sensors_65s.json',{}))));pages=read(A/'hub_pages.json',{});source=read(OUT/'source/manifest.json',{})
soak=read(ROOT/'output/accumulated_soak/status.json',{})
mp=bool(mqtt.get('full_requirement_pass'));op=bool(outage.get('passed'));np=bool(nvs.get('passed'))
def hours(ms):m=int(ms//60000);return f'{m//60} ชม. {m%60} นาที'
states={
'FR-01':(False,'บางส่วน',False,'ยังไม่ครบ',f"รุ่น 2.0.9 รับจริง {sensors.get('live','--')} รายการ/{round(sensors.get('observed_s',0))} s; env/pulse/acc/mag/INA/IAQ ทำงาน\nวางนิ้วรอบแรก SpO₂ valid 25/65; รอบล่าสุด {sensors.get('readiness',{}).get('spo2_valid',{}).get('true','--')}/{sensors.get('live','--')}; ยังไม่ปิดความถี่ถึงจอ; GY-51 ตามขอบเขตปรับ"),
'FR-02':(True,'แล้ว',True,'ผ่าน','ผู้ใช้ยืนยันเวลา แบต และสถานะตรงจริง; จอใหญ่แตะเปลี่ยนหน้าได้\nรุ่น 2.0.9/1.0.8 ตรวจคำสั่ง 11 หน้าและคืนหน้าเดิมได้; ไม่แทนทัช ≤300 ms'),
'FR-03':(True,'แล้ว',mp,'ผ่าน' if mp else 'รอตรวจ',f"ปรับ topic เป็น ku/iot/ku_watch/ku-watch-449205d4/env ผ่าน NVS และปรับฝั่งรับแล้ว\nตรวจ QoS1 {mqtt.get('live','--')} รายการ/{round(mqtt.get('observed_s',0))} วินาที; ลำดับขาด {mqtt.get('sequence_gaps','--')}; LWT มีจริง"),
'FR-04':(True,'แล้ว',True,'ช่วงที่ตรวจ','ไฟล์ 14 ต.ค. 1,408 แถว; รอบ 16 ต.ค. 61 แถว/5 นาที 1 วินาที เปิด Excel ครบ 26 คอลัมน์\nรอบ 16 ต.ค. RTC ต่าง ≤1 s; บันทึกห่าง 4–6 s; ไม่เหมารวมทุกช่วงหรือ 24 ชั่วโมง'),
'FR-05':(True,'แล้ว',op,'ผ่าน' if op else 'รอตรวจ',f"ตัด Wi-Fi จริง {outage.get('observed_offline_span_s',0):.1f} s; แฟลชเก็บค้างและส่งกลับเอง\nรับย้อนหลัง {outage.get('backfill_unique','--')} รหัส; DB ครบ {outage.get('database_capture_range',{}).get('captures','--')} รหัสในช่วงตรวจ; แยกจาก hub-offline CSV"),
'FR-06':(True,'แล้ว',False,'รอตรวจ','มีเกณฑ์ 3 รอบอ่านใหม่และภาพเตือนจริง\nIAQ อ่านราว 3 s/รอบ การรอ 3 รอบอาจเกิน 5 s; ยังไม่ปิดเกณฑ์เวลาถึงจอและ dashboard'),
'FR-07':(True,'แล้ว',np,'ผ่าน' if np else 'รอตรวจ','เปลี่ยน topic และค่าเตือนจริง รีบูตตรวจการคงค่า แล้วคืนเกณฑ์ 35°C/IAQ150 และรีบูตซ้ำ\nSSID/broker/topic คงเดิม; รายการกิจกรรมและขนาดไม่เปลี่ยน; ไม่ดาวน์โหลดพิกัดดิบ'),
'FR-08':(False,'บางส่วน',False,'รอปลายทาง','มี OTA/A-B และเลขรุ่นบนสถานะ แต่ manifest HTTPS ยังไม่ตั้งปลายทางใช้งานจริง\nUSB update ไม่แทนการดาวน์โหลดเวอร์ชันใหม่เองภายใน 24 ชั่วโมง'),
'NFR-01':(False,'ทดสอบอยู่',False,'รอครบ',f"MQTT สะสม {hours(soak.get('credited_ms',0))}; ต่อเนื่องยาวสุดเดิม {hours(soak.get('longest_continuous_ms',0))}\nเริ่มช่วงใหม่หลังทดสอบและรีบูต 16 ต.ค.; ยังไม่ผ่าน 24 ชั่วโมงต่อเนื่องหรืออายุแบต"),
'NFR-02':(True,'แล้ว',op,'ผ่าน' if op else 'รอตรวจ',f"ทดสอบ Wi-Fi หลุดจริง {outage.get('observed_offline_span_s',0):.1f} s นาฬิกายังอ่านเซ็นเซอร์และคิวทำงาน\nกลับ Wi-Fi/MQTT และระบายคิวเอง; ตรวจรหัสถึง DB ในผลเดียวกับ FR-05"),
'NFR-03':(True,'แล้ว',False,'ยังไม่ครบ','Grafana query เดิม 10 รหัสเฉลี่ย 3.091 s; ภาพและคลิปจริงรอบ 16 ต.ค. เก็บแล้ว\nยังไม่ใช่ผลจับ sensor-to-browser paint และทัชถึงภาพ ≤300 ms; ไม่ใช้ ACK แทนภาพจริง'),
'NFR-04':(False,'พักไว้',False,'ไม่ทดสอบ','ผู้ใช้ไม่มีที่ชาร์จ รอบนี้ใช้ USB; กลางแจ้งใช้แบต 1000 mAh เปลี่ยนเมื่อหมด\nยังไม่ทดสอบแบตถึง 20% นาน ≥6 h และกระแส INA226 ยังไม่สอบเทียบ'),
'NFR-05':(True,'แล้ว',False,'เฉพาะ ZIP','broker ยืนยันตัวตนและ TLS; source ZIP ล่าสุดตรวจค่ารหัสลับที่รู้จัก ไม่รวมไฟล์ส่วนตัว/เฟิร์มแวร์\nเพิ่ม ignore config/*.local.json; โฟลเดอร์นี้ยังไม่ใช่ Git repo จึงไม่อ้างตรวจ repo ที่เผยแพร่แล้ว'),
'NFR-06':(False,'บางส่วน',False,'รออ้างอิง','ไม่มีเทอร์โมมิเตอร์สำหรับเทียบ 10 จุด ±3°C\nชีพจร/SpO₂ เป็นค่าทดลอง; อุณหภูมิอาจได้รับความร้อนบอร์ด ไม่ปรับค่าเดาให้ตรงผลอ้างอิง'),
'NFR-07':(False,'รอราคา',False,'รอรวมงบ','เว้นราคาซื้อจริงและชื่อสมาชิกตามคำขอผู้ใช้\nยังไม่รวม BOM ทั้งชุดเทียบ ≤3,000 บาท ไม่ใช้ราคาประมาณเป็นผลผ่าน'),
'NFR-08':(True,'แล้ว',False,'รอทดสอบ','มีโมดูล A/B app0/app1 และห้าม OTA เมื่อแบต <30%\nยังไม่มีผลตัดไฟ OTA จริง 3 ครั้งและ rollback; การรีบูตทดสอบ NVS ไม่ใช้แทนข้อทดสอบนี้'),
}
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','w14':'http://schemas.microsoft.com/office/word/2010/wordml'}
W='{'+NS['w']+'}';XML='{http://www.w3.org/XML/1998/namespace}'
def txt(n):return ''.join(n.itertext()) if False else ''.join(n.xpath('.//w:t/text()',namespaces=NS))
def setp(p,text):
 runs=p.findall(W+'r');rpr=deepcopy(runs[0].find(W+'rPr')) if runs and runs[0].find(W+'rPr') is not None else None
 for node in list(p):
  if node.tag!=W+'pPr':p.remove(node)
 run=E.SubElement(p,W+'r')
 if rpr is not None:run.append(rpr)
 for i,line in enumerate(text.split('\n')):
  if i:E.SubElement(run,W+'br')
  t=E.SubElement(run,W+'t');t.set(XML+'space','preserve');t.text=line
def checkbox(cell,checked,label):
 node=cell.xpath('.//w14:checkbox/w14:checked',namespaces=NS)[0];node.set('{'+NS['w14']+'}val','1' if checked else '0')
 glyph=cell.xpath('.//w:sdtContent//w:t',namespaces=NS)[0];glyph.text='☑' if checked else '☐'
 paras=cell.findall(W+'p');setp(paras[-1],label)
with ZipFile(SRC) as z:parts={i.filename:(i,z.read(i.filename)) for i in z.infolist()}
tree=E.fromstring(parts['word/document.xml'][1]);count=0
for row in tree.xpath('.//w:tbl/w:tr',namespaces=NS):
 cells=row.findall(W+'tc')
 if len(cells)!=5:continue
 match=re.search(r'(?:NFR|FR)-\d\d',txt(cells[0]))
 if not match:continue
 rid=match[0];v=states[rid];checkbox(cells[2],v[0],v[1]);checkbox(cells[3],v[2],v[3]);paras=cells[4].findall(W+'p');setp(paras[0],v[4])
 for p in paras[1:]:setp(p,'')
 count+=1
assert count==16
now=datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=7)))
for p in tree.xpath('./w:body/w:p',namespaces=NS):
 text=txt(p)
 if text.startswith('สถานะ 14 ตุลาคม'):setp(p,f'สถานะ 16 ตุลาคม 2569 เวลา {now:%H:%M} น.   WATCH 2.0.9   HUB 1.0.8')
 if text.startswith('FR-04 ใช้ไฟล์'):setp(p,'หลักฐานรอบ 16 ต.ค. อยู่ในชุด final_acceptance_20261016 พร้อมผล MQTT ออฟไลน์ NVS CSV และการตรวจซอร์ส; ภาพและคลิปจริงรวมอยู่ในชุดสื่อวันนี้')
 if text.startswith('ต้นฉบับ Requirements V2'):setp(p,'เกณฑ์ Requirements V2 เดิมไม่เปลี่ยน ข้อที่ยังไม่ผ่านคงช่องว่างไว้ ราคาจริงและชื่อสมาชิกให้เติมเอง ผลจำลองไม่แทนผลจากเครื่องจริง และ USB ไม่แทนแบตเตอรี่')
newparts={'word/document.xml':E.tostring(tree,xml_declaration=True,encoding='UTF-8',standalone=True)}
for name,(info,data) in parts.items():
 if re.fullmatch(r'word/footer\d+\.xml',name):
  node=E.fromstring(data);changed=False
  for t in node.xpath('.//w:t',namespaces=NS):
   if t.text and '14 ตุลาคม 2569' in t.text:t.text=re.sub(r'14 ตุลาคม 2569(?: \d\d:\d\d)?',f'16 ตุลาคม 2569 {now:%H:%M}',t.text);changed=True
  if changed:newparts[name]=E.tostring(node,xml_declaration=True,encoding='UTF-8',standalone=True)
dest=OUT/'KU_Watch_ตารางตรวจรับก่อนนำเสนอ_16ตุลาคม2569.docx'
with ZipFile(dest,'w') as z:
 for name,(info,data) in parts.items():z.writestr(info,newparts.get(name,data))
with ZipFile(dest) as z:
 assert z.testzip() is None
 assert all(z.read(k)==v[1] for k,v in parts.items() if k not in newparts)
assert hashlib.sha256(SRC.read_bytes()).hexdigest()==EXPECTED
records=[]
original=read(ROOT/'output/deadline_20261018/requirements_original.json')['requirements']
for row in original:
 v=states[row['id']];records.append({**row,'implemented':v[0],'implementation_label':v[1],'accepted':v[2],'acceptance_label':v[3],'evidence_summary':v[4]})
comparison={'updated_thai':now.isoformat(),'source_reference_sha256':EXPECTED,'docx_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'native_checkbox_count':32,'accepted':[k for k,v in states.items() if v[2]],'requirements':records,'scope':'No pending, deferred or partial requirement is treated as accepted. Original criteria remain unchanged.'}
(OUT/'comparison.json').write_text(json.dumps(comparison,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'docx':str(dest),'accepted':comparison['accepted'],'checkboxes':32,'original_unchanged':True},ensure_ascii=False))
