"""Package the reviewed checklist, real media and scoped test evidence; no credentials."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,zipfile
from package_delivery import known_secrets
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/final_delivery_20261016'
comparison=json.loads((OUT/'comparison.json').read_text(encoding='utf8'))
accepted=comparison['accepted'];pending=[r['id'] for r in comparison['requirements'] if not r['accepted']]
readme='''KU Watch — ชุดพร้อมนำเสนอ 16 ตุลาคม 2569

Canva ฉบับบันทึกที่ผู้ใช้อนุมัติแล้ว: https://www.canva.com/d/grv_5b3tED4mGFk
14 หน้า; อัปเดตผลตรวจรับหน้า 7–9 และใส่คลิป Node-RED จริงหน้า 11 แล้ว

เริ่มจากเอกสาร Word ตารางตรวจรับ: ช่อง “ทำแล้ว” แยกจาก “ผ่านเกณฑ์” เกณฑ์ต้นฉบับไม่เปลี่ยน
ผ่านตามหลักฐานในขอบเขตที่ระบุ: ACCEPTED
ข้อที่ยังไม่ผ่านทั้งข้อ: PENDING

ลำดับเดโมแนะนำ
1. เปิดตัวเล็กและจอใหญ่ แสดงเวลา แบต และ NETWORK
2. เปลี่ยนหน้าด้วยปุ่มเดียว/ทัชจอใหญ่ แล้วแสดง ENVIRONMENT และ SD: CSV LOGGING
3. เปิดคลิปผู้ใช้ที่ถ่ายไว้ และคลิป Grafana/Node-RED จริงใน ZIP สื่อ
4. เปิดไฟล์ CSV จริงใน Excel แสดงหัวตารางและเวลา; ใช้ตาราง Word อธิบายข้อที่ยังรอ

ก่อนพรีเซ็นต์
- เปิดฮอตสปอตเดิม 2.4 GHz และอินเทอร์เน็ต จากนั้นรอ Wi-Fi/MQTT CONNECTED
- เดโมในอาคารใช้ USB; กลางแจ้งใช้แบตตามที่มี ยังไม่กล่าวอ้างแบตผ่าน 6 ชั่วโมง
- เว้นชื่อสมาชิกและราคาซื้อจริงให้ผู้ใช้เติม ไม่ใส่ราคาคาดเดาเป็นผลผ่าน
- เก็บคลิปผู้ใช้เดิมไว้ ช่องคลิปที่ว่างใน Canva ให้เติมจากไฟล์ของผู้ใช้

ขอบเขตหลักฐาน
- MQTT / ตัด Wi-Fi / NVS เป็นผลทดสอบจริงวันที่ 16 ต.ค. 2569 ดู evidence/20261016
- CSV และสื่อเก่ามีวันที่ของตนเอง ไม่ใช้เป็นผลทุกช่วงหรือผล 24 ชั่วโมง
- การเก็บ MQTT สะสมหลายช่วงไม่ใช่การทำงานต่อเนื่อง 24 ชั่วโมง และไม่ใช่อายุแบต
- ค่าอุณหภูมิอาจรับความร้อนบอร์ด; ชีพจรและ SpO2 เป็นค่าทดลอง ไม่ใช้วินิจฉัยโรค
- ซอร์ส ZIP ไม่มีไฟล์ config ส่วนตัวหรือ firmware ที่มี credentials; ต้องตั้งค่าท้องถิ่นก่อน build
- PowerPoint ใน source ZIP เป็นสำเนา 15 ต.ค. ก่อนปรับผลตรวจรับล่าสุด ให้ยึด Word 16 ต.ค. และ Canva ฉบับที่อนุมัติล่าสุด
'''.replace('ACCEPTED',', '.join(accepted)).replace('PENDING',', '.join(pending))
(OUT/'อ่านก่อนนำเสนอ.txt').write_text(readme,encoding='utf8')
files={}
for p in OUT.glob('*.docx'):files[p.name]=p
for p in [OUT/'comparison.json',OUT/'อ่านก่อนนำเสนอ.txt',OUT/'source/manifest.json',OUT/'canva_saved.json']:
 files[p.relative_to(OUT).as_posix()]=p
for p in (OUT/'source').glob('*.zip'):files['source/'+p.name]=p
media=ROOT/'output/KU_Watch_ภาพและคลิปจริงวันนี้_16ตุลาคม2569.zip';files['media/'+media.name]=media
recovery=ROOT/'output/final_acceptance_20261016/recovery_clip_visible'
for p in recovery.glob('*'):
 if p.suffix in {'.mp4','.png','.json'}:files['media/offline_recovery/'+p.name]=p
for name in ['mqtt_5min_canonical.json','topic_migration.json','nvs_reboot.json','sensors_65s_after.json','sensors_finger_65s.json','sensors_finger_stable_65s.json','hub_pages.json','script_checks.json','offline_10min/result.json','long_monitor_resumed.json','dashboard_scale.json']:
 p=ROOT/'output/final_acceptance_20261016'/name
 if p.exists():files['evidence/20261016/'+name]=p
secrets=known_secrets()
def audit(name,data):
 if any(s in data for s in secrets):raise RuntimeError('Known credential found in '+name)
 if name.endswith('.zip'):
  from io import BytesIO
  with zipfile.ZipFile(BytesIO(data)) as z:
   if z.testzip():raise RuntimeError('Corrupt nested archive')
   for n in z.namelist():audit(name+'/'+n,z.read(n))
hashes={}
for name,p in files.items():
 data=p.read_bytes();audit(name,data);hashes[name]=hashlib.sha256(data).hexdigest()
manifest={'created_utc':datetime.now(timezone.utc).isoformat(),'accepted':accepted,'pending':pending,'known_secret_scan_passed':True,'files':hashes,'boundary':'Actual dated evidence only; partial tests are not full requirements acceptance.'}
target=OUT/'KU_Watch_ชุดพร้อมนำเสนอ_16ตุลาคม2569.zip'
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
 for name,p in files.items():z.write(p,name)
 z.writestr('MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2))
with zipfile.ZipFile(target) as z:
 assert z.testzip() is None
 for name,h in hashes.items():assert hashlib.sha256(z.read(name)).hexdigest()==h
(OUT/'bundle_manifest.json').write_text(json.dumps({**manifest,'archive':target.name,'archive_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'bytes':target.stat().st_size},ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'archive':str(target),'accepted':accepted,'files':len(files),'bytes':target.stat().st_size,'known_secret_scan_passed':True},ensure_ascii=False))
