"""Freeze the observed FR results without changing original criteria or evidence."""
from pathlib import Path
from copy import deepcopy
from datetime import datetime, timezone, timedelta
from zipfile import ZipFile
import argparse, hashlib, json, re
from lxml import etree as E

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / 'output/fr_completion_20261016'
parser=argparse.ArgumentParser();parser.add_argument('--revision',default='')
args=parser.parse_args()
FW='2.0.15'
if args.revision and not re.fullmatch(r'[A-Za-z0-9_-]+',args.revision):raise ValueError('Use a portable revision name')
suffix='_'+args.revision if args.revision else ''
OUT = RUN / 'deliverable' / args.revision
OUT.mkdir(exist_ok=True,parents=True)
SRC = ROOT / 'output/final_delivery_20261016/KU_Watch_ตารางตรวจรับก่อนนำเสนอ_16ตุลาคม2569.docx'
EXPECTED = '6b348512951bbf809343c89a01837d7c1e433c59b9347012b7140842fe159a25'
assert hashlib.sha256(SRC.read_bytes()).hexdigest() == EXPECTED
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
baseline = read(ROOT / 'output/final_delivery_20261016/comparison.json')
records = {r['id']: dict(r) for r in baseline['requirements']}
mqtt = read(RUN / 'mqtt_2.0.12_normal_5min.json')
transport_files=sorted((RUN/'mqtt_transport_runs').glob('*/comparison.json'))
transport=read(transport_files[-1]) if transport_files else None
if transport:mqtt=transport['modes'][transport['primary_mode']]
home_audit=RUN/'mqtt_2.0.15_pc_home_5min.json'
if home_audit.exists():mqtt=read(home_audit)
fr06_dir = sorted((RUN/'fr06_runs').glob('*/fr06_hardware_browser.json'))[-1].parent
fr06 = read(fr06_dir / 'fr06_hardware_browser.json')
fr06_count=len(fr06['tests'])
fr06_display_max=max((x.get('display_elapsed_ms') or 0 for x in fr06['tests']),default=0)/1000
fr06_browser_max=max((x.get('browser_elapsed_ms') or 0 for x in fr06['tests']),default=0)/1000
ota_file=sorted(RUN.glob('fr08_auto_update_'+FW+'*.json'))[-1]
version_file=sorted(RUN.glob('fr08_mqtt_version_'+FW+'*.json'))[-1]
ota = read(ota_file)
version = read(version_file)
fr01 = read(RUN / 'fr01_active_status.json')
local_pointer=read(RUN/'fr01_local_latest.json') if (RUN/'fr01_local_latest.json').exists() else None
local=read(Path(local_pointer['result'])) if local_pointer else None
fr01_pass=bool(local and local.get('fr01_full_pass') and local.get('expected_firmware')==FW and local.get('firmware_identity_verified'))
visual_path=RUN/('user_visual_confirmation_'+FW+'.json')
visual=read(visual_path) if visual_path.exists() else {}
fr08_pass=bool(ota['passed'] and version['passed'] and visual.get('fr08_visual_acceptance_confirmed'))
soak = read(ROOT / 'output/accumulated_soak/status.json')
now = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=7)))
thai_date=f'{now.day} ตุลาคม {now.year+543}'

def change(rid, implemented, accepted, label, evidence):
    records[rid].update(implemented=implemented,
                        implementation_label='แล้ว' if implemented else 'บางส่วน',
                        accepted=accepted, acceptance_label=label,
                        evidence_summary=evidence)

change('FR-01', True, fr01_pass, 'ผ่าน' if fr01_pass else 'ยังไม่ครบทุกเกณฑ์',
       'รุ่น 2.0.15 อ่าน PPG จริง 25 Hz และตรวจจอหลังส่ง SPI; IAQ ใช้รอบ BSEC 3 s\n'+
       ('ตรวจ USB โดยตรง ผ่านช่วง BPM/SpO₂ valid ต่อเนื่อง ≥60 s พร้อมความถี่จอ; ไม่ใช้ความช้า MQTT มาตัดช่วงจอ' if fr01_pass else
        'รุ่น 2.0.14 มี BPM/SpO₂ valid 69.9 s แต่ภาพช้าสุด 1.027 s; ผลรุ่น 2.0.15 ยังไม่ผ่านครบทุกเกณฑ์'))
change('FR-03', True, bool(mqtt['full_requirement_pass']), 'ผ่าน' if mqtt['full_requirement_pass'] else 'รอบล่าสุดไม่ผ่าน',
       f"รุ่น 2.0.15 คอมผ่าน Wi-Fi บ้าน รับ {mqtt['live']} รายการ/300 s หาย {mqtt['sequence_gaps']} หลุด {mqtt['disconnects']}\n"
       f"QoS1/LWT ตรวจจริง ช่องว่างรับสูงสุด {mqtt['max_receive_gap_ms']/1000:.2f} s; ใช้ guard เดิม <3 s")
change('FR-06', True, bool(fr06['passed']), 'ผ่าน\nค่าจำลอง' if fr06['passed'] else 'ยังไม่ผ่าน',
       'ทดสอบ TEMP และ IAQ โดยป้อน 3 ค่าใหม่ที่ 1 Hz ตามวิธีจำลองในเกณฑ์\n'+
       f"รอบล่าสุด {sum(x['passed'] for x in fr06['tests'])}/{fr06_count} จอช้าสุด {fr06_display_max:.2f} s และ browser {fr06_browser_max:.2f} s; TEST ไม่ลงข้อมูลจริง")
change('FR-08', True, fr08_pass, 'ผ่าน' if fr08_pass else 'รอยืนยันเลขบนจอ',
       'OTA อัตโนมัติ HTTPS สำเร็จถึง 2.0.15 ตรวจ SHA256 และบูตยืนยันสุขภาพ; /status ตรง 2.0.15\n'+
       ('ผู้ใช้ยืนยันเห็น FW 2.0.15 บนตัวเล็กและ WATCH 2.0.15 บนจอใหญ่ตรงกันแล้ว' if fr08_pass else
        'ตรวจ NETWORK ส่งภาพลงจอแล้ว แต่ยังรอผู้ใช้ยืนยันเลขรุ่นที่มองเห็น'))
assert ota['passed'] and version['passed']

def hours(ms):
    minutes = int(ms // 60000)
    return f'{minutes//60} ชม. {minutes%60} นาที'

records['NFR-01']['evidence_summary'] = (
    f"MQTT สะสม {hours(soak.get('credited_ms',0))}; ต่อเนื่องยาวสุด {hours(soak.get('longest_continuous_ms',0))}\n"
    'ยังไม่ครบ 24 ชั่วโมงต่อเนื่อง; แยกรอบล้มเหลวเดิม และไม่ใช้ผลนี้แทนอายุแบตเตอรี่')
records['NFR-05']['evidence_summary'] = (
    'Source ZIP รุ่น 2.0.15 ตรวจค่ารหัสลับที่รู้จัก ไม่รวม config ส่วนตัวและไฟล์เฟิร์มแวร์\n'
    'เพิ่ม ignore กุญแจ TLS ส่วนตัว; ยังไม่ได้เผยแพร่ Git repo จึงไม่อ้างผลตรวจ repo')
records['NFR-08']['evidence_summary'] = (
    'อัปเดต A/B ผ่าน Wi-Fi จริง app0→app1→app0 และตรวจ hash/health หลังบูต\n'
    'ยังไม่ทดสอบตัดไฟระหว่าง OTA 3 ครั้งและ rollback จึงยังไม่ผ่าน NFR-08')

NS = {'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
      'w14':'http://schemas.microsoft.com/office/word/2010/wordml'}
W = '{'+NS['w']+'}'
XML = '{http://www.w3.org/XML/1998/namespace}'

def txt(node):
    return ''.join(node.xpath('.//w:t/text()', namespaces=NS))

def setp(p, value):
    runs = p.findall(W+'r')
    props = deepcopy(runs[0].find(W+'rPr')) if runs and runs[0].find(W+'rPr') is not None else None
    for node in list(p):
        if node.tag != W+'pPr': p.remove(node)
    run = E.SubElement(p,W+'r')
    if props is not None: run.append(props)
    for index, line in enumerate(value.split('\n')):
        if index: E.SubElement(run,W+'br')
        t = E.SubElement(run,W+'t'); t.set(XML+'space','preserve'); t.text = line

def checkbox(cell, checked, label):
    cell.xpath('.//w14:checkbox/w14:checked', namespaces=NS)[0].set('{'+NS['w14']+'}val', '1' if checked else '0')
    cell.xpath('.//w:sdtContent//w:t', namespaces=NS)[0].text = '☑' if checked else '☐'
    setp(cell.findall(W+'p')[-1], label)

with ZipFile(SRC) as z:
    parts = {i.filename:(i,z.read(i.filename)) for i in z.infolist()}
tree = E.fromstring(parts['word/document.xml'][1])
criteria = {}
for row in tree.xpath('.//w:tbl/w:tr', namespaces=NS):
    cells = row.findall(W+'tc')
    if len(cells)!=5: continue
    match = re.search(r'(?:NFR|FR)-\d\d', txt(cells[0]))
    if not match: continue
    rid = match[0]; value = records[rid]; criteria[rid] = txt(cells[1])
    checkbox(cells[2], value['implemented'], value['implementation_label'])
    checkbox(cells[3], value['accepted'], value['acceptance_label'])
    paras = cells[4].findall(W+'p'); setp(paras[0], value['evidence_summary'])
    for p in paras[1:]: setp(p,'')
assert len(criteria)==16
for p in tree.xpath('./w:body/w:p', namespaces=NS):
    text = txt(p)
    if text.startswith('สถานะ 16 ตุลาคม'):
        setp(p, f'สถานะ {thai_date} เวลา {now:%H:%M} น.   WATCH {FW}   HUB 1.0.8')
    elif text.startswith('หลักฐานรอบ 16 ต.ค.'):
        setp(p, 'ผลล่าสุดอยู่ในชุด FR_Status_2.0.15 พร้อมหลักฐานแจ้งเตือน OTA การตรวจสัญญาณจริง และผล MQTT ทั้งที่ผ่านและไม่ผ่าน ผลเดิมคงวันและรุ่นไว้ตามจริง')
    elif text.startswith('เกณฑ์ Requirements V2'):
        setp(p, 'เกณฑ์ Requirements V2 เดิมไม่เปลี่ยน ช่องที่ยังไม่ผ่านคงว่างไว้ FR-06 ใช้วิธีจำลองตามเกณฑ์ FR-01 วัดที่เครื่องโดยตรง และ FR-08 ยืนยันเลขรุ่นจากจอจริงแล้ว')
changed = {'word/document.xml':E.tostring(tree,xml_declaration=True,encoding='UTF-8',standalone=True)}
for name, (_, data) in parts.items():
    if re.fullmatch(r'word/footer\d+\.xml',name):
        node = E.fromstring(data); touched = False
        for t in node.xpath('.//w:t', namespaces=NS):
            if t.text and '16 ตุลาคม 2569' in t.text:
                t.text = re.sub(r'16 ตุลาคม 2569(?: \d\d:\d\d)?', f'{thai_date} {now:%H:%M}', t.text); touched = True
        if touched: changed[name] = E.tostring(node,xml_declaration=True,encoding='UTF-8',standalone=True)
dest = OUT/('KU_Watch_FR_Status_'+FW+suffix+'.docx')
if dest.exists():raise FileExistsError('Preserve the earlier snapshot; choose a new revision')
with ZipFile(dest,'w') as z:
    for name, (info,data) in parts.items(): z.writestr(info,changed.get(name,data))
with ZipFile(dest) as z:
    assert z.testzip() is None
    assert all(z.read(k)==v[1] for k,v in parts.items() if k not in changed)
    after = E.fromstring(z.read('word/document.xml'))
    controls = after.xpath('.//w14:checkbox',namespaces=NS)
    assert len(controls)==32
    for row in after.xpath('.//w:tbl/w:tr',namespaces=NS):
        cells=row.findall(W+'tc')
        if len(cells)!=5: continue
        match=re.search(r'(?:NFR|FR)-\d\d',txt(cells[0]))
        if match: assert txt(cells[1]) == criteria[match[0]]
assert hashlib.sha256(SRC.read_bytes()).hexdigest()==EXPECTED

snapshot = {'updated_thai':now.isoformat(), 'watch_version':FW, 'hub_version':'1.0.8',
            'accepted':[k for k,v in records.items() if v['accepted']],
            'requirements':list(records.values()), 'source_docx_sha256':EXPECTED,
            'docx_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),
            'original_criteria_unchanged':True, 'native_checkbox_count':32,
            'fr01_observer_at_snapshot':fr01,'fr01_local_observation':local_pointer,
            'fr08_visual_confirmation':visual,
            'latest_ota_evidence':str(ota_file),'latest_mqtt_version_evidence':str(version_file),
            'latest_fr06':str(fr06_dir/'fr06_hardware_browser.json'),
            'latest_mqtt_transport_comparison':str(transport_files[-1]) if transport_files else None,
            'latest_mqtt_audit':str(home_audit) if home_audit.exists() else None,
            'boundary':'A dated snapshot. No pending, failed or partial result counts as accepted.'}
(OUT/'comparison.json').write_text(json.dumps(snapshot,ensure_ascii=False,indent=2),encoding='utf8')
summary = f'''# KU Watch ผลตรวจรับเฟิร์มแวร์ {FW}

สถานะ ณ {now:%d/%m/%Y %H:%M} น. ประเทศไทย จอใหญ่ 1.0.8 เกณฑ์เดิมไม่เปลี่ยน ผลผ่านตรวจจากหลักฐานแต่ละรายการ

| ข้อ | ผลล่าสุด | หลักฐานและงานที่เหลือ |
| --- | --- | --- |
'''
for rid,v in records.items():
    if rid.startswith('FR-'):
        summary+=f"| {rid} | {'ผ่าน' if v['accepted'] else v['acceptance_label']} | {v['evidence_summary'].replace(chr(10),' ')} |\n"
summary+='''
## การแก้ไขและขอบเขตหลักฐาน

รุ่น 2.0.15 ลดเวลาส่งภาพด้วยการเปรียบเทียบพิกเซลแต่ละแถบกับภาพก่อนหน้าแบบตรงทุกไบต์ ส่งเฉพาะแถบที่เปลี่ยน โดยคง SPI 2 MHz บังคับส่งเต็มภาพหลังเปลี่ยนหน้า รีเซ็ต หรือทดสอบแจ้งเตือน หาก PSRAM ไม่พอจะใช้วิธีส่งเต็มภาพเดิม ผลตรวจรีเฟรชประเมินเมื่อพิกเซลทั้งจอตรงกับแบบจำลองปัจจุบัน ไม่ปรับเกณฑ์เวลาเพื่อให้ผ่าน

FR-01 ใช้ MAX30102 อ่านจริง 25 Hz โดยปรับแสง IR และแดงเป็น 31 เพื่อให้ระดับแสงไม่อิ่มตัว รุ่น 2.0.14 หาคาบจริงด้วยการลบแนวโน้มเชิงเส้นและ autocorrelation ทั้งสองช่อง โดยแสดง BPM จากคาบที่คำนวณใหม่ รักษาการตรวจคุณภาพ ความสัมพันธ์ ช่วง SpO₂ และการปฏิเสธสัญญาณที่ไม่มีคาบ ไม่บีบค่าให้อยู่ในช่วงหรือคงสถานะ valid เก่าทับช่วงสัญญาณเสีย รอบก่อนหน้าที่ไม่ผ่านเก็บแยกไว้ การปรับนี้ไม่ใช่การสอบเทียบทางการแพทย์

FR-03 เปรียบเทียบการรับสามแบบบนฮอตสปอตแล้วพบช่วงรับช้า ทั้งที่รหัสไม่หาย จึงเปลี่ยนเฉพาะคอมเป็น Wi-Fi บ้านและทดสอบ 300 s อีกครั้ง นาฬิกายังใช้ SS เกณฑ์ QoS1 ลำดับข้อความ จำนวนที่ 1 Hz LWT และช่องว่างรับ <3 s ไม่เปลี่ยน ผลเวลาที่ไม่ผ่านยังคงไว้

FR-06 หลักฐานรุ่น 2.0.12 ป้อนค่า TEMP และ IAQ อย่างละสองครั้ง ใช้ 3 ค่าใหม่ที่ 1 Hz ผ่าน 4/4 จอช้าสุด 3.276 s และ browser 3.563 s ภาพกับคลิปแสดง TEST ชัดเจน ไม่มีค่าจำลองเข้าฐานข้อมูลจริง วิธีจำลองนี้อนุญาตในเกณฑ์เดิม และไม่ใช้ปิด NFR-03 ของ Grafana

FR-08 อัปเดต HTTPS อัตโนมัติจริง 2.0.10 → 2.0.11 → 2.0.12 → 2.0.13 → 2.0.14 → 2.0.15 ตรวจ SHA256 และยืนยันสุขภาพหลังบูต รุ่น 2.0.14 ครั้งแรกดาวน์โหลดหรือ hash ไม่สำเร็จ เครื่องคงแอปเก่าไว้ การลองใหม่สำเร็จในราว 87 s อยู่ใน fr08_auto_update_2.0.14_retry1.json ไม่อัปโหลดเฟิร์มแวร์ผ่าน USB และไม่ส่ง OTACHECK ผู้ใช้ยืนยันเลขบนสองจอตรง 2.0.15 แล้ว /status ตรงกัน ระบบกำหนดตรวจตอนบูตและทุก 24 ชั่วโมง แต่ยังไม่ได้รอครบคาบ 24 ชั่วโมงจริง

เซิร์ฟเวอร์ OTA เป็น HTTPS บนคอมใน LAN ของ SS ต้องเปิดคอมและให้นาฬิกาเข้าถึงได้ ค่าปลายทางและกุญแจส่วนตัวไม่รวมในชุดส่งต่อ ค่าตั้ง LED/red เปลี่ยนอย่างตั้งใจระหว่างทดลอง ส่วนไฟล์ WALK ตรวจ hash โดยไม่บันทึกพิกัดหรือชีพจรดิบเพิ่ม

การเปลี่ยนวิธีประเมิน PPG ระบุไว้ก่อนทดสอบจริงใน ppg_algorithm_change_2.0.14.json อ้างอิงแนวทาง MAX30102_by_RF ที่ https://github.com/aromring/MAX30102_by_RF ใช้ autocorrelation เทียบ lag ศูนย์ที่ 0.5 ตามวิธีเผยแพร่ โดยตรวจทั้ง IR และแดง พร้อม Pearson ≥0.90 แทนวิธีตรวจยอดคลื่นกับเกณฑ์ภายในเดิม 0.85/0.75 เกณฑ์ตรวจรับต่อเนื่องหนึ่งนาทีไม่เปลี่ยน รอบนี้เป็นการทดสอบฟังก์ชัน ไม่ใช่การสอบเทียบทางการแพทย์

ผลทดสอบ host ที่ใช้ยืนยันอยู่ในรอบ 20261016T154226Z เปิด assertions จริงด้วย -UNDEBUG ผ่าน 8 ชุด C++ และ OTA gateway รอบเดิมที่ assertions ไม่ทำงานไม่ใช้เป็นหลักฐานผ่าน

NFR-01 เวลารับ MQTT สะสมแยกจากเวลาต่อเนื่องยาวที่สุด ยังไม่ผ่าน 24 ชั่วโมงต่อเนื่อง และไม่ใช้แทนอายุแบตเตอรี่ ผลแบตเตอรี่ 6 ชั่วโมง การสอบเทียบอ้างอิง งบจริง และการตัดไฟระหว่าง OTA 3 ครั้งยังไม่ผ่าน

## การเปิดชุดหลักฐาน

เปิด Word ดูช่องติ๊กและเกณฑ์เดิม README นี้สรุปผลปัจจุบัน evidence/ เก็บ JSON ทั้งผ่านและไม่ผ่าน media/ มีภาพและคลิปแจ้งเตือนจากค่าจำลอง historical/ กับไฟล์เดิมใน source ZIP เป็นหลักฐานตามวันและรุ่นนั้น ไม่ใช่ผลทดสอบซ้ำของ 2.0.15 ซอร์สไม่รวมรหัสผ่าน กุญแจส่วนตัว สำเนาแฟลช หรือไฟล์ .bin เฉพาะเครื่อง
'''
if local:
    summary+='\n## ผล FR-01 ล่าสุด\n\n'+json.dumps({k:local[k] for k in ['mode','metrics','cadence_pass','quality_observations','valid_quality_observations','longest_observed_valid_span_s','fr01_full_pass']},ensure_ascii=False,indent=2)+'\n'
summary+='\n## ผล FR-03 ล่าสุด\n\n'+json.dumps({k:mqtt[k] for k in ['live','sequence_gaps','duplicates','disconnects','max_receive_gap_ms','full_requirement_pass']},ensure_ascii=False,indent=2)+'\n'
summary+=f'\n## ผลแจ้งเตือนรุ่นปัจจุบัน\n\nรอบล่าสุด {fr06_count} กรณี ผ่าน {sum(x["passed"] for x in fr06["tests"])} กรณี จอช้าสุด {fr06_display_max:.3f} s เบราว์เซอร์ช้าสุด {fr06_browser_max:.3f} s รายงานอยู่ใน {fr06_dir.name} ส่วนภาพและคลิปชื่อ FR06_Actual_Browser_Test เป็นหลักฐานรุ่น 2.0.12 ที่เก็บไว้ ภาพและคลิปชื่อ FR06_2.0.15 เป็นรอบปัจจุบัน\n'
(OUT/('FR_Status_'+FW+suffix+'.md')).write_text(summary,encoding='utf8')
print(json.dumps({'docx':str(dest),'accepted':snapshot['accepted'],
                  'original_criteria_unchanged':True,'checkboxes':32},ensure_ascii=False))
