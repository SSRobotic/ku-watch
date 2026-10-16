"""Package only verified real screenshots and selected measurement evidence."""
from pathlib import Path
from datetime import datetime, timezone
import json, hashlib, shutil, zipfile, html

root = Path(__file__).resolve().parents[1]
source = root / 'output/presentation_evidence/actual_tools'
out = root / 'output/presentation_evidence/slide_evidence_20261014'
out.mkdir(parents=True, exist_ok=True)
images = []

def copy(file, target):
    destination = out / target
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        assert destination.read_bytes() == file.read_bytes(), 'Preserve existing package content'
    else:
        shutil.copy2(file, destination)
    return destination

captions = {
    '01_nodered_flow_fit.png': ('Node-RED — ผังการรับข้อมูล', 'ภาพหน้าโปรแกรมจริง แสดง flow รับ MQTT และส่งต่อฐานข้อมูล จัดมุมมอง Zoom to fit โดยไม่ได้ Deploy'),
    '02_nodered_dashboard.png': ('Node-RED — Dashboard', 'กราฟค่าจริงบน Node-RED Dashboard; รูปนาฬิกาด้านบนเป็นภาพเดิมที่บันทึกไว้ ไม่ใช่ภาพถ่ายเครื่อง ณ เวลาจับหน้าจอ'),
    '01_influx_count.png': ('InfluxDB — ตรวจจำนวนข้อมูล', 'ผล SQL API จริง: 896 แถว และ 896 sample_id ที่ไม่ซ้ำในช่วงข้อมูลที่ระบุ ใช้ Pretty-print ของเบราว์เซอร์ ไม่ใช่หน้า InfluxDB Explorer'),
    '02_influx_records.png': ('InfluxDB — แถวที่บันทึกจริง', 'ผล SQL API จริง แสดงเวลา sample_id อุณหภูมิ ความชื้น IAQ และแรงดันแบต 3 แถวล่าสุด'),
    '01_temperature.png': ('Grafana — อุณหภูมิ', 'กราฟอุณหภูมิจากข้อมูลจริง ยังไม่ใช่ผลสอบเทียบกับเทอร์โมมิเตอร์'),
    '02_humidity.png': ('Grafana — ความชื้น', 'กราฟความชื้นจากข้อมูลจริง'),
    '03_iaq.png': ('Grafana — IAQ', 'กราฟ IAQ จากเซ็นเซอร์จริง เป็นค่าประมาณของเซ็นเซอร์'),
    '04_battery_voltage.png': ('Grafana — แรงดันแบต', 'แรงดันจาก INA226 ขณะทดสอบด้วย USB ไม่ใช้เป็นผลทดสอบอายุแบตหรือกระแสที่สอบเทียบแล้ว'),
    '05_acceleration.png': ('Grafana — การเคลื่อนไหว', 'ค่าความเร่งดิบ 3 แกนจากข้อมูลจริง ไม่ใช่ผลสอบเทียบหรือผลตรวจไจโร'),
    '06_iaq_alert.png': ('Grafana — สถานะเตือน IAQ', 'ภาพสถานะเกินเกณฑ์จากข้อมูลจริง ณ เวลาจับภาพ ยังไม่ใช่ผลทดสอบเวลาตอบสนองการเตือน'),
    '07_pressure.png': ('Grafana — ความกดอากาศ', 'กราฟความกดอากาศจากข้อมูลจริง'),
}
sets = [('20261014T075333Z_details', ['01_nodered_flow_fit.png', '02_nodered_dashboard.png']),
        ('20261014T075931Z_influx', ['01_influx_count.png', '02_influx_records.png']),
        ('20261014_grafana_in_app', list(captions)[4:])]
for folder, names in sets:
    manifest = json.loads((source / folder / 'manifest.json').read_text(encoding='utf8'))
    copy(source / folder / 'manifest.json', 'sources/' + folder + '/manifest.json')
    for record in manifest['images']:
        if record['file'] not in names:
            continue
        file = source / folder / record['file']
        assert hashlib.sha256(file.read_bytes()).hexdigest() == record['sha256']
        title, caption = captions[file.name]
        relative = 'images/' + file.name
        copy(file, relative)
        images.append(dict(record, file=relative, title=title, caption=caption, visual_reviewed=True))
    if folder.endswith('_influx'):
        for name in names:
            for suffix in ['.json', '.sql']:
                p = source / folder / (Path(name).stem + suffix)
                copy(p, 'database/' + p.name)

# Regenerate this older caption file to match its corrected original manifest.
details = source / '20261014T075333Z_details'
dm = json.loads((details / 'manifest.json').read_text(encoding='utf8'))
(details / 'captions.md').write_text('\n\n'.join(f"{r['file']} — {r['captured_thai']}\n{r['caption']}" for r in dm['images']), encoding='utf8')

sd = root / 'output/deadline_20261018/sd_acceptance_longer'
for name in ['env_1791956522_e47806b1.csv', 'env_1791956522_e47806b1.csv.audit.json', 'excel_open.json']:
    copy(sd / name, 'sd_evidence/' + name)
assert hashlib.sha256((out / 'sd_evidence/env_1791956522_e47806b1.csv').read_bytes()).hexdigest() == '856a6391997ef453a7bacb70e79a953302603fb3d7e64422f47cfcbaeda6072c'
word = root / 'output/deadline_20261018/requirements_accepted_20261014'
wm = json.loads((word / 'manifest.json').read_text())
copy(word / wm['docx'], 'requirements/' + wm['docx'])
copy(word / 'comparison.json', 'requirements/comparison.json')

notes = '''# ภาพจริงสำหรับสไลด์ KU Watch — 14 ตุลาคม 2569

ภาพ PNG จับจากโปรแกรมจริง ไม่ได้สร้างภาพกราฟหรือเติมข้อมูลจำลอง แยกเวลาจับภาพออกจากช่วงข้อมูลที่แสดงไว้ใน manifest.json พร้อม SHA-256 ของแต่ละภาพ

Grafana ใช้หน้า ku-watch-live ที่ผู้ใช้ล็อกอินอยู่ในแอป ไม่ใช้ dashboard สาธิต ข้อมูล InfluxDB เป็นผล SQL API ของ InfluxDB 3 Core ไม่ใช่ภาพหน้า Explorer รูปนาฬิกาที่อยู่ใน Node-RED Dashboard เป็นภาพเดิม ไม่ใช่ภาพเครื่อง ณ เวลาจับหน้าจอ

ตรวจรับ FR-02 ด้านการแสดงผลและทัชตามคำยืนยันผู้ใช้ ส่วน FR-04 ตรวจไฟล์ MicroSD จริง 1,408 แถว ครอบคลุม 1 h 57 min 32 s และเปิดใน Excel ได้ 26 คอลัมน์ เวลา RTC/Watch ต่างไม่เกิน 2 s รอบเวลาจำนวนเต็ม 4–6 s ไม่พบช่วงขาดเกิน 6 s ในไฟล์นี้

ภาพเหล่านี้ไม่ได้ยืนยันการทำงานต่อเนื่อง 24 ชั่วโมง อายุแบต 6 ชั่วโมง การสอบเทียบเซ็นเซอร์ หรือผ่าน Requirements ทุกข้อ ชีพจร/SpO₂ ในช่วงจับภาพนี้ยังรอข้อมูล เกณฑ์ที่ยังไม่ได้ทดสอบไม่ติ๊กผ่านใน Word

ไฟล์ CSV และ audit อยู่ใน sd_evidence ส่วนหลักฐาน SQL และผลจริงอยู่ใน database นำภาพจาก images ไปวางในสไลด์พร้อมคำบรรยายด้านล่างได้
'''
for r in images:
    notes += f"\n## {r['title']}\n\nไฟล์: {r['file']}\n\nเวลาจับภาพ (ไทย): {r['captured_thai']}\n\n{r['caption']}\n"
(out / 'คำอธิบายภาพสำหรับสไลด์.md').write_text(notes, encoding='utf8')
manifest = dict(type='ACTUAL_TOOL_EVIDENCE_PACKAGE', created_utc=datetime.now(timezone.utc).isoformat(), images=images,
    boundary='Actual screenshots and preserved real observations. Not a full-system, 24-hour continuous or battery-runtime pass.')
(out / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf8')
cards = ''.join(f'<article><h2>{html.escape(r["title"])}</h2><p>{html.escape(r["captured_thai"])}</p><a href="{r["file"]}"><img src="{r["file"]}" alt="{html.escape(r["title"])}"></a><p>{html.escape(r["caption"])}</p></article>' for r in images)
(out / 'index.html').write_text('<!doctype html><html lang="th"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>KU Watch — ภาพจริงสำหรับสไลด์</title><style>body{font:18px Tahoma,sans-serif;background:#edf2f7;color:#152238;margin:0;padding:28px}main{max-width:1300px;margin:auto}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:24px}article{background:white;padding:20px;border-radius:12px}img{width:100%;height:420px;object-fit:contain;background:#15191d}h1{font-size:30px}h2{font-size:22px}p{line-height:1.7}a{color:#1255a5}</style><main><h1>KU Watch — ภาพจริงสำหรับสไลด์</h1><p>14 ตุลาคม 2569 · พร้อมเวลาจับภาพและไฟล์ต้นฉบับ คลิกภาพเพื่อเปิดขนาดเต็ม</p><p>ภาพแสดงข้อมูลที่รับหรือบันทึกได้จริงในช่วงที่ระบุ ผลทดสอบ 24 ชั่วโมงและอายุแบตยังไม่ได้ผ่าน</p><div class="grid">' + cards + '</div></main></html>', encoding='utf8')
archive = out.parent / 'KU_Watch_ภาพจริงและหลักฐานสำหรับสไลด์_14ตุลาคม2569.zip'
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
    for p in sorted(out.rglob('*')):
        if p.is_file():
            z.write(p, p.relative_to(out))
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    assert not any('.browser-private' in n or '.capture-private' in n for n in z.namelist())
assert len(images) >= 10
print(json.dumps(dict(archive=str(archive), images=len(images), sha256=hashlib.sha256(archive.read_bytes()).hexdigest(), all_image_hashes_verified=True), ensure_ascii=False))
