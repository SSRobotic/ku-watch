"""Refresh handoff status from recorded evidence, retaining historical sections."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
AUDIT=ROOT/'output/requirements_audit_20261009'
def replace(name,old,new):
    path=ROOT/name;text=path.read_text(encoding='utf8')
    if old not in text:raise RuntimeError('Expected text absent: '+name)
    path.write_text(text.replace(old,new),encoding='utf8')
def prepend(name,text):
    path=ROOT/name;original=path.read_text(encoding='utf8');path.write_text(text+'\n\n'+original,encoding='utf8')
outage=json.loads((AUDIT/'broker_outage.json').read_text())
sensor=json.loads((AUDIT/'sensors_65s.json').read_text())
pages=json.loads((AUDIT/'hub_all_pages.json').read_text())
preserve=json.loads((AUDIT/'completion_preserve_after.json').read_text())
if not (outage['passed'] and sensor['transport_pass'] and pages['all_pages_matched'] and preserve['unchanged']):raise RuntimeError('Final verification must pass')
soak=json.loads((ROOT/'output/soak_audit/status.json').read_text())
latest=f'''## ผลล่าสุด — ตัวเล็ก 2.0.5 / จอใหญ่ 1.0.5

- ผู้ใช้ยืนยันปิดตัวเล็กแล้วเปิดใหม่เวลาตรง โดยเปิดจอใหญ่ไว้ รุ่นนี้เพิ่มเวลาย้อนจาก RTC จอใหญ่ผ่าน ESP-NOW ที่จับคู่แล้ว เมื่อเวลาตัวเล็กยังไม่พร้อม ผลนี้ไม่ยืนยัน RTC หลังดับทั้งสองบอร์ด
- เก็บ sample_id เป็น tag ใน InfluxDB แยกcapturesวินาทีเดียวและใช้จุดเดิมเมื่อส่งซ้ำ ทดสอบ5capturesจริงและส่งตัวแรกซ้ำ2ครั้ง SQLพบหนึ่งรายการต่อรหัส
- พอร์ต MQTT ติดต่อไม่ได้จริง600วินาที ขณะWi-Fiยังอยู่ คืนพอร์ต8883แล้วคิวหมด dropped=0/storage_errors=0; DBครบ600ข้อมูลช่วงขาด ตรวจช่วงรหัสต่อเนื่อง889รหัสครบ ไม่มีลำดับขาด ผลsubscriberช่วงแรก361backfillsและSQLครบเป็นคนละหลักฐาน ดู broker_outage.json
- ทดสอบหลังปิดเว็บตั้งค่า: MQTTจริง{sensor['live']}ตัวอย่างใน65วินาที รุ่น2.0.5; env/pulse/acc/mag/battery/INA/IAQ/GPSพร้อม; SpO₂ไม่พร้อมและcurrent_valid=falseในช่วงนี้ ไม่มีBSEC error ไม่ใช้readinessแทนaccuracy
- จอใหญ่/ตัวเล็กตรงกัน11/11หน้า ค่าตั้งและSHA256ไฟล์WALK3/6/7ยังเหมือนเดิม เว็บตั้งค่าปฏิเสธคำขอผิดรูปแบบโดยไม่รีสตาร์ต
- ทดสอบhost C++15ชุด/Python/Nodeผ่าน; FR-06ป้อน3ค่าใหม่จำลอง1Hzเตือน2007ms ผ่านmodel+renderer+methodการ์ด ยังไม่ยืนยันBSECจริง/แสงจอ/Grafana paintภายใน5s
- เปิดรับMQTTเพื่อตรวจ24ชั่วโมง เริ่ม {soak['started_utc']} (UTC); สถานะตอนจัดชุดส่งมอบคือ running ไม่ถือว่าผ่าน24ชั่วโมง ต้องเปิดคอม/เน็ต/บอร์ดต่อเนื่อง ดู output/soak_audit/status.json

ขณะทดสอบคำขอเว็บผิดรูปแบบพร้อมเปลี่ยนหน้า เคยพบESP-NOWขาดช่วงและ65วินาทีได้59ข้อความ จึงเก็บผลไว้ใน hub_pages_during_portal_probes.json/sensors_during_portal_probes.json ไม่ลบผลที่ไม่ผ่าน เมื่อปิดเว็บและตรวจซ้ำพบเมนูครบ11/11และtransportผ่าน ขอบเขตนี้ยังไม่ใช่การยืนยันความหน่วงภายใต้HTTP stress

ยังข้าม: สอบเทียบINA/เครื่องมือวัดอุณหภูมิและPPG, FR-06จริง≤5s, browser paint, แบต6hจากแบตเต็ม, ผล24h, RTCbackup/ไฟย้อน, WALKเส้นทางจริง, OTAตัดไฟ3ครั้ง, HTTPS OTAอัตโนมัติ ชื่อ/บทบาท/ราคาซื้อยังเว้นตามคำขอ ภาพ/วิดีโอในสไลด์เป็นช่องให้ใส่ไฟล์จริง

สไลด์ล่าสุด output/delivery_20261009/KU_Watch_ตามเกณฑ์ประเมิน_25691009_v2.pptx และ source KU_Watch_Source_2.0.5_Hub_1.0.5.zip มีหลักฐานและคู่มือ ดู ตรวจรับ_รอบต่อ.md ข้อมูลรุ่นเก่าด้านล่างเป็นประวัติ ไม่แทนผลรุ่นใหม่ทุกข้อ
'''
replace('รายงาน_ผลระบบล่าสุด.md','วันที่ 9 ตุลาคม 2569 · ตัวเล็ก 2.0.3 · จอใหญ่ 1.0.4','วันที่ 9 ตุลาคม 2569 · ตัวเล็ก 2.0.5 · จอใหญ่ 1.0.5')
replace('รายงาน_ผลระบบล่าสุด.md','## วัตถุประสงค์และขอบเขต',latest+'\n## วัตถุประสงค์และขอบเขต')
replace('ส่งมอบ_อ่านก่อน.md','OTA HTTPS อัตโนมัติ, broker outage 10 นาที, browser paint latency','OTA HTTPS อัตโนมัติ, browser paint latency')
prepend('ความต้องการ_สถานะล่าสุด.md',latest)
prepend('README_เริ่มตรงนี้.md','> **รุ่นล่าสุด 2.0.5 / Hub1.0.5:** เวลาย้อนจากRTCจอใหญ่, DBแยกcaptureและreplay, MQTTขาด10นาทีDBครบ600ข้อมูล; เริ่มตรวจ24hแล้วแต่ยังไม่ครบ ดู [ผลและรายการข้าม](ตรวจรับ_รอบต่อ.md) และ [คู่มือส่งมอบ](ส่งมอบ_อ่านก่อน.md) ประวัติรุ่นเก่าด้านล่างยังคงไว้')
print('Handoff documents refreshed from actual passing evidence.')
