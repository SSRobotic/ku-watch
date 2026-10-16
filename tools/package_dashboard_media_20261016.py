"""Copy verified real captures and trim actual video; never synthesize measurements."""
from pathlib import Path
import hashlib,json,shutil,subprocess,html,zipfile
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/presentation_media_20261016'
OUT.mkdir(parents=True,exist_ok=True)
SRC=ROOT/'output/presentation_evidence/slide_evidence_20261014'
source_manifest=json.loads((SRC/'manifest.json').read_text(encoding='utf8'))
records=[]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def copy(source,destination):
    destination.parent.mkdir(parents=True,exist_ok=True)
    if destination.exists():
        assert digest(source)==digest(destination),'Refuse to overwrite different media'
    else:shutil.copy2(source,destination)
for i,r in enumerate(source_manifest['images'],1):
    source=SRC/r['file']
    assert digest(source)==r['sha256']
    dest=OUT/'01_ภาพแดชบอร์ดจริง'/Path(r['file']).name
    copy(source,dest)
    records.append({**r,'file':str(dest.relative_to(OUT)).replace('\\','/'),'copied_without_changes':True})

video_dir=OUT/'02_วิดีโอแดชบอร์ดจริง'
video_dir.mkdir(exist_ok=True)
source_video=ROOT/'output/outdoor_capture/20261014T102621009Z/NodeRED_actual_outdoor.webm'
dest_video=video_dir/'NodeRED_ข้อมูลไหลจริง_60วินาที_บันทึก14ตุลา2569.mp4'
if not dest_video.exists():
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-n','-ss','6','-i',str(source_video),'-t','60','-an','-c:v','libx264','-preset','fast','-crf','24','-pix_fmt','yuv420p','-movflags','+faststart',str(dest_video)],check=True)
probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration:stream=codec_name,width,height','-of','json',str(dest_video)],text=True))
assert 59.9<=float(probe['format']['duration'])<=60.1
assert probe['streams'][0]['codec_name']=='h264'
video_record={'file':str(dest_video.relative_to(OUT)).replace('\\','/'),'title':'Node-RED: ข้อมูลและกราฟเปลี่ยนตามเวลาจริง','captured_date_thai':'14 ตุลาคม 2569','duration_s':float(probe['format']['duration']),'source':str(source_video.relative_to(ROOT)).replace('\\','/'),'source_sha256':digest(source_video),'sha256':digest(dest_video),'source_start_s':6,'playback_speed':1,'editing':'Trim and encode to MP4 only. No changed pixels apart from lossy encoding; no added values or accelerated time. Original preserved.','boundary':'Recorded Node-RED web dashboard, not a physical LCD mirror, not a recording of today. No battery/endurance/latency pass inferred.'}
copy(ROOT/'output/outdoor_capture/20261014T102621009Z/00_20261014T102626072Z.json',OUT/'03_ที่มาและเวลา'/'video_start_actual_query.json')
copy(ROOT/'output/outdoor_capture/20261014T102621009Z/01_20261014T102726527Z.json',OUT/'03_ที่มาและเวลา'/'video_next_minute_actual_query.json')
manifest={'created_utc':datetime.now(timezone.utc).isoformat(),'images':records,'videos':[video_record],'originals_unchanged':True,'source_type':'ACTUAL_RECORDED_TOOL_OUTPUT','boundary':'All source captures are from 14 Oct 2026. A recording played today does not establish fresh device readings today. No fabricated pass, measurements, locations or raw PPG.'}
(OUT/'03_ที่มาและเวลา').mkdir(exist_ok=True)
(OUT/'03_ที่มาและเวลา'/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
guide='''ชุดภาพและคลิปสำหรับเสริมสไลด์ KU Watch

ภาพ 10 ภาพ: Grafana / Node-RED / InfluxDB เป็นภาพที่จับจากโปรแกรมจริง 14 ตุลาคม 2569 ไม่ใช่ข้อมูลสดวันนี้
คลิป MP4 60 วินาที: ตัดจากวิดีโอ Node-RED จริงช่วงต้น ความเร็ว 1 เท่า กราฟและค่าขยับจากอุปกรณ์จริงขณะบันทึก ไม่ได้สร้างข้อมูลเพิ่ม

แนะนำใส่สไลด์
หน้า 5: ภาพ 01_nodered_flow_fit แสดง backend ที่ใช้งานจริง
หน้า 11: คลิป NodeRED_ข้อมูลไหลจริง เป็นคลิปเสริมของคุณ หรือเพิ่มหน้าเฉพาะถ้าต้องการเปิดเต็มจอ
หน้า 12: Grafana 01_temperature / 02_humidity / 03_iaq และ InfluxDB 01_influx_count / 02_influx_records
ภาพแบตเป็นแรงดันขณะทดสอบ ไม่ใช้แทนผลทดสอบแบต 6 ชั่วโมง
ภาพแจ้งเตือนไม่ใช้แทนผลจับเวลาเตือนภายใน 5 วินาที
รูปนาฬิกาในภาพ Node-RED เป็นภาพเดิม ไม่ใช่กล้องถ่ายทอดสดจากหน้าจอจริง

วิธีเพิ่มใน Canva
1 เปิดฉบับนำเสนอ https://www.canva.com/d/H5TTIBYNLX_3Wu8
2 อัปโหลดไฟล์จากโฟลเดอร์ 01_ภาพแดชบอร์ดจริง และ 02_วิดีโอแดชบอร์ดจริง
3 ลากลงหน้า จัดขนาด แล้วใส่คำบรรยาย บันทึกจริง 14 ตุลาคม 2569
4 ทดสอบ Present และกดเล่นก่อนวันนำเสนอ

ภาพและไฟล์ฐานข้อมูลต้นทางไม่ถูกแก้ไข ไฟล์ manifest มีเวลาจับภาพและ SHA-256 ให้ตรวจสอบ
'''
(OUT/'อ่านก่อนใช้.txt').write_text(guide,encoding='utf8')
cards=[]
for r in records:
    f=html.escape(r['file']);title=html.escape(r.get('title',Path(r['file']).stem));caption=html.escape(r.get('caption',''));stamp=html.escape(r.get('captured_thai',r.get('captured_utc','')))
    cards.append(f'<article><h2>{title}</h2><a href="{f}"><img src="{f}"></a><p>{stamp}</p><p>{caption}</p></article>')
v=html.escape(video_record['file'])
(OUT/'เปิดดูภาพและคลิป.html').write_text('<!doctype html><meta charset="utf-8"><title>KU Watch — ภาพและคลิปจริง</title><style>body{font:18px Tahoma;background:#f4f7f6;color:#243631;max-width:1440px;margin:auto;padding:30px}h1{color:#26725c}.grid{display:grid;grid-template-columns:1fr 1fr;gap:24px}article{background:white;border:1px solid #dbe3df;padding:20px}img{width:100%;max-height:550px;object-fit:contain}p{line-height:1.7}video{width:100%;max-height:750px;background:#111}a{color:#18634e}</style><h1>KU Watch — ภาพและคลิปจากโปรแกรมจริง</h1><p>บันทึกจริง 14 ตุลาคม 2569 · เปิดคลิปที่บันทึกไว้ ไม่ใช่ข้อมูลสดวันนี้</p><video controls preload="metadata" src="'+v+'"></video><p>Node-RED 60 วินาที ความเร็วเดิม 1 เท่า · คลิกภาพเพื่อดูขนาดเต็ม</p><div class="grid">'+''.join(cards)+'</div>',encoding='utf8')
zip_path=ROOT/'output/KU_Watch_ภาพและคลิปแดชบอร์ดจริง_พร้อมใช้สไลด์_16ตุลา2569.zip'
with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
    for f in sorted(OUT.rglob('*')):
        if f.is_file():z.write(f,f.relative_to(OUT))
with zipfile.ZipFile(zip_path) as z:assert z.testzip() is None
print(json.dumps({'images':len(records),'video':str(dest_video),'duration_s':video_record['duration_s'],'zip':str(zip_path),'zip_bytes':zip_path.stat().st_size,'originals_unchanged':True},ensure_ascii=False))
