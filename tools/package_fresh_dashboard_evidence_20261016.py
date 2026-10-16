from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,shutil,zipfile,html,subprocess

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'output/presentation_media_20261016'
OUT=ROOT/'output/slide_media_actual_20261016'
OUT.mkdir(exist_ok=True)
items=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def cp(source,relative,title,caption,stamp=None):
    dest=OUT/relative;dest.parent.mkdir(parents=True,exist_ok=True)
    if dest.exists():assert sha(source)==sha(dest),'Keep prior evidence unchanged'
    else:shutil.copy2(source,dest)
    item={'file':relative,'title':title,'caption':caption,'source_file':str(source.relative_to(ROOT)).replace('\\','/'),'sha256':sha(dest),'captured_utc':stamp};items.append(item)
    return dest
live=BASE/'live_capture/20261016T072138979Z'
lm=json.loads((live/'manifest.json').read_text(encoding='utf8'))
assert lm['fresh_sample_progressed'] and lm['all_observations_fresh']
for name in ['NodeRED_0s.png','NodeRED_50s.png']:
    r=next(i for i in lm['images'] if i['file']==name)
    assert sha(live/name)==r['sha256']
    cp(live/name,'ภาพวันนี้/'+name,'Node-RED — กราฟข้อมูลจริง','บอร์ดเชื่อมต่อจริงขณะบันทึก ภาพเว็บ ไม่ใช่ภาพถ่ายทอดจาก LCD',r['captured_utc'])
cp(live/'manifest.json','หลักฐาน/NodeRED_capture_manifest.json','หลักฐานการอัด Node-RED','sample_id เปลี่ยนและข้อมูลใหม่ตลอดช่วงที่ตรวจ')
video=live/'NodeRED_สด_16ตุลา2569_60วินาที.mp4'
duration=float(json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','json',str(video)],text=True))['format']['duration'])
assert abs(duration-60)<.1
cp(video,'คลิปวันนี้/NodeRED_กราฟและข้อมูลไหลจริง_16ตุลา2569_60วินาที.mp4','Node-RED — คลิปจริง 60 วินาที','ความเร็วเดิม 1 เท่า ตัดจากการอัดหน้าเว็บจริง 16 ตุลาคม 2569 ไม่สร้างค่าหรือเร่งเวลา',lm['recording_started_utc'])
details=BASE/'backend_details';dm=json.loads((details/'manifest.json').read_text(encoding='utf8'))
for r in dm['images']:
    name=r['file'];assert sha(details/name)==r['sha256']
    caption='ภาพ editor จริง: จุดเขียว connected / Saved to durable DB queue แสดงสถานะ; กล่องสีแดงชื่อ DB offline เป็นชื่อทางดักข้อผิดพลาด ไม่ใช่ผลว่าฐานข้อมูลล่มอยู่'
    if name.startswith('Influx'):caption='ผลตอบกลับ SQL API ของ InfluxDB จริงพร้อมเวลา UTC ไม่ใช่หน้า Explorer และไม่ใช้ยืนยันผ่านครบทุก requirement'
    cp(details/name,'ภาพวันนี้/'+name,name.replace('_',' ').removesuffix('.png'),caption,r['captured_utc'])
for f in sorted(details.glob('*.json')):cp(f,'หลักฐาน/'+f.name,'ผล query / แหล่งที่มา','ค่าที่อ่านจริงจากฐานข้อมูล ไม่แก้ไข')
for f in sorted(details.glob('*.sql')):cp(f,'หลักฐาน/'+f.name,'SQL ที่ใช้ตรวจ','SELECT แบบอ่านอย่างเดียว')
sd=BASE/'current_sd_export'
for f in sorted(sd.iterdir()):
    if f.is_file() and (f.suffix=='.csv' or f.name.endswith('.audit.json') or f.name=='excel_open.json'):
        cp(f,'CSV_เปิดในExcelได้/'+f.name,'MicroSD / Excel','ข้อมูลจริง 61 แถว 26 คอลัมน์ ช่วง5นาที1วินาที; ไม่ใช่การทดสอบต่อเนื่อง24ชม.')
grafana_manifests=sorted((BASE/'live_capture').glob('*_grafana/manifest.json'))
grafana_included=False
for manifest in grafana_manifests:
    gm=json.loads(manifest.read_text(encoding='utf8'))
    if gm.get('status')!='captured':continue
    gf=manifest.parent
    for r in gm['images']:
        if r['file'] in ['Grafana_live_0s.png','Grafana_live_50s.png','Grafana_temperature.png','Grafana_humidity.png','Grafana_iaq.png','Grafana_acceleration.png','Grafana_battery_voltage.png','Grafana_iaq_alert.png']:
            assert sha(gf/r['file'])==r['sha256']
            captions={
                'Grafana_temperature.png':'อุณหภูมิจากเซ็นเซอร์จริง ยังไม่ผ่านการเทียบเทอร์โมมิเตอร์ อาจมีผลจากความร้อนสะสมของบอร์ด',
                'Grafana_battery_voltage.png':'แรงดัน INA226 ขณะทดสอบด้วย USB ไม่ใช่ผลอายุแบต6ชั่วโมงหรือการสอบเทียบกระแส',
                'Grafana_iaq_alert.png':'สถานะแจ้งเตือนจริงจากข้อมูลที่รับ ไม่ใช่ผลจับเวลาเตือนภายใน5วินาที',
                'Grafana_acceleration.png':'ค่าความเร่งจริง3แกน ไม่ใช่ข้อมูลไจโรหรือผลสอบเทียบ',
                'Grafana_iaq.png':'IAQจริงจากBSEC ยังไม่ใช่การรับรองความแม่นยำของคุณภาพอากาศ',
            }
            cp(gf/r['file'],'ภาพวันนี้/'+r['file'],'Grafana — '+r['file'].removesuffix('.png'),captions.get(r['file'],'หน้า Grafana จริง16ตุลาคม2569 ค่าชีพจรเป็นค่าทดลอง ยังไม่ได้เทียบเครื่องมืออ้างอิง'),r['captured_utc'])
    if (gf/'Grafana_สด_16ตุลา2569_60วินาที.mp4').exists():cp(gf/'Grafana_สด_16ตุลา2569_60วินาที.mp4','คลิปวันนี้/Grafana_สด_16ตุลา2569_60วินาที.mp4','Grafana — คลิปจริง 60 วินาที','อัดจาก Grafana จริง ความเร็วเดิม ไม่มีการสร้างข้อมูล',gm['recording_started_utc'])
    cp(manifest,'หลักฐาน/Grafana_capture_manifest.json','แหล่งที่มา Grafana','ข้อมูลบันทึกเวลาและSHA-256')
    grafana_included=True
if (BASE/'canva_grafana_assets.json').exists():cp(BASE/'canva_grafana_assets.json','หลักฐาน/Canva_Grafana_media.json','สื่อที่เพิ่มในคลังCanva','ชื่อและรหัสสื่อที่อัปโหลดสำเร็จ ไม่ใช่การเปลี่ยนเลย์เอาต์สไลด์')
report={'created_utc':datetime.now(timezone.utc).isoformat(),'date':'2026-10-16','boundary':'Actual tool outputs and recorded UI only. Does not certify all requirements, medical accuracy, display latency, battery runtime or 24-hour continuity. Private profiles and credentials are excluded.','grafana_current_capture_included':grafana_included,'items':items}
(OUT/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
text='''ชุดเสริมสไลด์ KU Watch — บันทึกจริง 16 ตุลาคม 2569

ตัวเล็ก COM15 / จอใหญ่ COM8
ข้อมูลเข้า Node-RED และ InfluxDB จริง ก่อนเริ่มอัดตรวจว่า sample_id เดินหน้าและข้อมูลใหม่
วิดีโอ Node-RED 60 วินาที MP4 ความเร็วเดิม 1 เท่า อัดจากกราฟหน้าเว็บ ไม่ใช่การแชร์ LCD
CSV รอบนี้ 61 แถว 26 คอลัมน์ ครอบคลุม5นาที1วินาที ช่วงบันทึก4–6วินาที เวลา RTC ต่างจากตัวเล็กมากสุด1วินาที
เปิด CSV ด้วย Microsoft Excel16 แบบอ่านอย่างเดียวได้แล้ว SHA-256 ไม่เปลี่ยน
ทั้งหมดเป็นผลเฉพาะช่วงที่ตรวจ ไม่ใช่ผลผ่าน24ชั่วโมง แบต6ชั่วโมง หรือสอบเทียบเซ็นเซอร์

เพิ่มใน Canva: Uploads → เลือกภาพหรือ MP4 → ลากลงหน้า → ตั้งเล่นเมื่อคลิก → ทดลอง Present
สไลด์ที่จัดไว้: https://www.canva.com/d/H5TTIBYNLX_3Wu8
ยังไม่ได้เปลี่ยนเลย์เอาต์หรือแทนคลิปส่วนตัวในงาน Canva ของคุณ อัปโหลดสื่อเสริมเข้าคลัง Canva ให้แล้ว
'''
text+='\nGrafana รอบวันนี้: '+('รวมอยู่ในชุดแล้ว\n' if grafana_included else 'กำลังรอการล็อกอินในเบราว์เซอร์จับภาพ; ภาพ14ตุลาเดิมอยู่ในชุดแยก ไม่ปนกับภาพวันนี้\n')
(OUT/'อ่านก่อนใช้.txt').write_text(text,encoding='utf8')
cards=[]
for r in items:
    if not r['file'].endswith(('.png','.mp4')):continue
    f=html.escape(r['file']);media=f'<video controls preload="metadata" src="{f}"></video>' if f.endswith('.mp4') else f'<a href="{f}"><img src="{f}"></a>'
    cards.append('<article><h2>'+html.escape(r['title'])+'</h2>'+media+'<p>'+html.escape(r.get('captured_utc') or '')+'</p><p>'+html.escape(r['caption'])+'</p></article>')
(OUT/'เปิดดูภาพและคลิป.html').write_text('<!doctype html><meta charset="utf-8"><title>KU Watch — สื่อจริง16ตุลา2569</title><style>body{font:18px Tahoma;color:#263a32;background:#f3f7f5;padding:24px;max-width:1500px;margin:auto}.grid{display:grid;grid-template-columns:1fr 1fr;gap:24px}article{padding:20px;background:white;border:1px solid #dce4df}img,video{width:100%;max-height:650px;object-fit:contain}p{line-height:1.7}</style><h1>KU Watch — ภาพและคลิปจากอุปกรณ์จริง 16 ตุลาคม 2569</h1><p>ข้อมูลจริง ณ เวลาที่บันทึก · ยังไม่ใช่ผลผ่านทุกข้อกำหนด</p><div class="grid">'+''.join(cards)+'</div>',encoding='utf8')
archive=ROOT/'output/KU_Watch_ภาพและคลิปจริงวันนี้_16ตุลาคม2569.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for f in sorted(OUT.rglob('*')):
        if f.is_file():z.write(f,f.relative_to(OUT))
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    assert not any(x in n.lower() for n in z.namelist() for x in ['private','token','config.h','.log'])
print(json.dumps({'archive':str(archive),'items':len(items),'grafana_included':grafana_included,'bytes':archive.stat().st_size},ensure_ascii=False))
