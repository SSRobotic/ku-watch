"""Build the complete v2 handoff from allowlisted real media and validated PPTX."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,shutil,zipfile,html,importlib.util,lxml.etree as E
ROOT=Path(__file__).resolve().parents[1]
B=ROOT/'output/ppt_history_v2_20261016/build';OUT=B.parent/'deliverable'
PACKAGE=OUT/'KU_Watch_พร้อมนำเสนอ_v2';MEDIA=PACKAGE/'ภาพและคลิป'
SOURCE_MEDIA=ROOT/'output/ppt_academic_20261016/deliverable/KU_Watch_ภาพและคลิป'
history=json.loads((B/'history_manifest.json').read_text('utf8'))
final=OUT/'KU_Watch_นำเสนอพร้อมภาพพัฒนาการ_v2.pptx'
receipt=json.loads((B/'final_validation_ready.json').read_text('utf8'))
play=json.loads((B/'native_playback_verified.json').read_text('utf-8-sig'))
assert receipt['finalSha256']==hashlib.sha256(final.read_bytes()).hexdigest()==play['sha256']
assert play['passed'] and len(play['videos'])==10 and all(x['valid'] for x in play['links'])
fidelity=json.loads((B/'source_fidelity.json').read_text('utf8'));assert len(fidelity['unmodified_slides_pixel_identical'])+len(fidelity['source_slides_with_only_navigation_added'])==64 and not fidelity['unmodified_slides_with_visual_difference']
PACKAGE.mkdir(parents=True,exist_ok=True)
shutil.copytree(SOURCE_MEDIA,MEDIA,dirs_exist_ok=True)
entries=json.loads((SOURCE_MEDIA/'manifest.json').read_text('utf8'))['files']
def add(source,folder,name,title,scope,date):
    source=Path(source);dest=MEDIA/folder/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest)
    entries.append({'file':dest.relative_to(MEDIA).as_posix(),'title':title,'scope':scope,'date':date,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'bytes':dest.stat().st_size})
for i,item in enumerate(history['images'],1):
    source=Path(item['source']);assert hashlib.sha256(source.read_bytes()).hexdigest()==item['source_sha256']
    add(source,'09_ภาพพัฒนาการ',f'{i:02}_{item["id"]}{source.suffix.lower()}',item['title'],'ภาพพัฒนาการเดิม จัดตามขั้นตอนงาน ไม่ใช้วันที่บนจอเก่าเป็นผลตรวจเวลา','ภาพเดิมจากผู้ใช้')
for pdf in history['pdfs']:
    source=Path(pdf['source']);assert hashlib.sha256(source.read_bytes()).hexdigest()==pdf['sha256']
    title='แบบประกอบเชิงกล Rev A' if pdf['id']=='drawing' else 'แบบวงจร Rev A'
    add(pdf['image'],'10_แบบออกแบบ',pdf['id']+'.png',title+' — ภาพเต็มหน้า','ภาพเรนเดอร์จากเอกสาร PDF เดิม ไม่ใช่แบบ As-built ปัจจุบัน','16 ก.ย. 2569 ตามหน้าแบบ')
    add(source,'10_แบบออกแบบ',source.name,title+' — PDF ต้นฉบับ','เอกสารออกแบบเดิม เก็บไฟล์ต้นฉบับไว้เพื่อเปิดซูมรายละเอียด','16 ก.ย. 2569 ตามหน้าแบบ')
add(history['video']['source'],'11_คลิปพัฒนาการ','KU_Watch_ต้นแบบระหว่างพัฒนา_30วินาที.mp4','คลิปต้นแบบระหว่างพัฒนา 30 วินาที','คลิปต้นฉบับครบความยาว ไม่เปลี่ยนความเร็ว','คลิปเดิมจากผู้ใช้')
manifest={'created_utc':datetime.now(timezone.utc).isoformat(),'boundary':'Real development media and actual dashboard evidence. Historical design Rev A differs from the current assembled hardware. Cumulative MQTT reception is not continuous duration or battery endurance.','duplicates_not_repeated':2,'files':entries}
(MEDIA/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),'utf8')
cards=[]
ordered=[x for x in entries if x['file'].startswith(('09_','10_','11_'))]+[x for x in entries if not x['file'].startswith(('09_','10_','11_'))]
for item in ordered:
    url=html.escape(item['file'],quote=True);title=html.escape(item['title']);scope=html.escape(item['scope']);date=html.escape(item['date'])
    lower=item['file'].lower()
    if lower.endswith('.mp4'):visual=f'<video src="{url}" controls preload="metadata"></video>'
    elif lower.endswith(('.png','.jpg','.jpeg')):visual=f'<a href="{url}" target="_blank"><img src="{url}" loading="lazy" alt="{title}"></a>'
    elif lower.endswith('.pdf'):visual=f'<a class="file" href="{url}" target="_blank">เปิดแบบ PDF ต้นฉบับเพื่อซูม</a>'
    else:visual=f'<a class="file" href="{url}">เปิด CSV ต้นฉบับ</a>'
    cards.append(f'<article>{visual}<h2>{title}</h2><p>{date} · {scope}</p><a href="{url}" download>เปิด/บันทึกไฟล์เต็ม</a></article>')
page='''<!doctype html><html lang="th"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>KU Watch — ภาพพัฒนาการและหลักฐาน</title><style>body{margin:0;background:#eef1f5;color:#223040;font:17px "Leelawadee UI",Tahoma,sans-serif}header{background:#1e3a5f;color:white;padding:40px max(5vw,24px)}header p{max-width:1100px;line-height:1.8}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(400px,1fr));gap:24px;padding:30px}article{padding:18px;background:white;border:1px solid #d5dce4}img,video{width:100%;height:340px;object-fit:contain;background:#182027}h2{font-size:21px;margin:14px 0 8px}p{font-size:15px;line-height:1.7}a{color:#2469a1}.file{display:block;padding:120px 0;text-align:center}@media(max-width:500px){main{display:block}article{margin-bottom:20px}}</style><header><h1>KU Watch — ภาพพัฒนาการและหลักฐาน</h1><p>เริ่มจากภาพออกแบบ การประกอบ ปัญหาที่พบ และคลิปพัฒนาการ ตามด้วยภาพและคลิปแดชบอร์ดจริงจากชุดก่อนหน้า คลิกภาพเพื่อดูขนาดเต็ม แบบ Rev A เป็นเอกสารออกแบบเดิม มีรายละเอียดบางจุดต่างจากเครื่องปัจจุบัน</p></header><main>'''+''.join(cards)+'</main></html>'
(MEDIA/'เปิดดูภาพและคลิป.html').write_text(page,'utf8')
readme='''KU Watch — ชุดนำเสนอพร้อมภาพพัฒนาการ v2

เปิดไฟล์ PowerPoint ในโฟลเดอร์นี้ แล้วกด F5 คลิกวิดีโอเพื่อเล่น
มี 81 หน้า: 14 หน้าหลักและ 67 หน้าภาคผนวก
หน้า 2 มีภาพสรุปพัฒนาการและลิงก์เปิดภาพใหญ่
หน้า 14 และหน้า 15 ใช้เปิดสารบัญภาคผนวก
ทุกหน้าภาคผนวกมีปุ่มก่อนหน้า/ถัดไปสำหรับไล่ดูภาพที่ซ่อนไว้
ภาพพัฒนาการใหม่อยู่หน้า 67–81 คลิปใหม่อยู่หน้า 80
วิดีโอฝังใน PowerPoint แล้ว 10 ตำแหน่ง เล่นได้โดยไม่ต่ออินเทอร์เน็ต
ชื่อสมาชิก บทบาท และราคาซื้อจริงยังเว้นไว้ให้เติม

โฟลเดอร์ภาพและคลิป: เปิด “เปิดดูภาพและคลิป.html” เพื่อเลือกภาพขนาดเต็ม
มีภาพ 138 ภาพ คลิปต้นฉบับ 8 คลิป เอกสาร PDF 2 ฉบับ และ CSV จริง
ภาพที่ผู้ใช้ส่งมารอบใหม่มี 25 รายการ เป็นภาพไม่ซ้ำ 23 ภาพ จึงเก็บภาพซ้ำครั้งเดียว
แบบ Drawing และ Schematic เป็น Rev A เดิม 16 ก.ย. 2569 ไม่ใช่แบบ As-built รุ่นปัจจุบัน
ภาพพัฒนาการแสดงทั้งการทำงานและปัญหาที่พบ ไม่ใช้แทนการตรวจผ่าน Requirements
ผลรับ MQTT สะสมครบ 24 ชั่วโมงต่างจากการรับต่อเนื่อง 24 ชั่วโมงและอายุแบตเตอรี่
'''
(PACKAGE/'อ่านก่อนนำเสนอ_v2.txt').write_text(readme,'utf8');(MEDIA/'อ่านก่อนใช้สื่อ.txt').write_text(readme,'utf8')
shutil.copyfile(final,PACKAGE/final.name)
# Validate embedded original bytes, native hidden-slide counts and configured secrets.
spec=importlib.util.spec_from_file_location('delivery',ROOT/'tools/package_delivery.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);secrets=module.known_secrets()
with zipfile.ZipFile(final) as z:
    assert z.testzip() is None
    names=z.namelist();slides=[n for n in names if n.startswith('ppt/slides/slide') and n.endswith('.xml')]
    assert len(slides)==81
    assert sum(E.fromstring(z.read(n)).get('show')=='0' for n in slides)==67
    hashes={hashlib.sha256(z.read(n)).hexdigest() for n in names if n.startswith('ppt/media/') and n.endswith('.mp4')}
    assert len(hashes)==10
    oldplan=json.loads((ROOT/'output/ppt_academic_20261016/build/deck_plan.json').read_text('utf8'))
    for job in oldplan['videos']:assert hashlib.sha256(Path(job['file']).read_bytes()).hexdigest() in hashes
    assert history['video']['sha256'] in hashes
    for n in names:
        if n.endswith(('.xml','.rels')):assert not any(s in z.read(n) for s in secrets),'Configured credential in PPTX XML'
for file in MEDIA.rglob('*'):
    if file.is_file():assert not any(s in file.read_bytes() for s in secrets),'Configured credential in public media'
for item in entries:assert hashlib.sha256((MEDIA/item['file']).read_bytes()).hexdigest()==item['sha256']
checks=[]
for file in [PACKAGE/final.name,PACKAGE/'อ่านก่อนนำเสนอ_v2.txt',MEDIA/'manifest.json']:
    checks.append(f'{hashlib.sha256(file.read_bytes()).hexdigest()}  {file.relative_to(PACKAGE).as_posix()}')
(PACKAGE/'SHA256SUMS.txt').write_text('\n'.join(checks)+'\n','utf8')
archive=OUT/'KU_Watch_พร้อมนำเสนอ_รวมภาพพัฒนาการ_v2.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for file in sorted(PACKAGE.rglob('*')):
        if file.is_file():z.write(file,file.relative_to(OUT).as_posix())
with zipfile.ZipFile(archive) as z:assert z.testzip() is None
report={'archive':str(archive),'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'archive_bytes':archive.stat().st_size,'pptx_sha256':receipt['finalSha256'],'images':sum(x['file'].lower().endswith(('.png','.jpg','.jpeg')) for x in entries),'videos':sum(x['file'].endswith('.mp4') for x in entries),'pdfs':sum(x['file'].lower().endswith('.pdf') for x in entries),'media_files':len(entries),'all_media_hashes_verified':True,'known_secret_scan_passed':True,'native_playback_verified':True,'internal_links_verified':len(play['links']),'source_slides_unchanged':64,'changed_or_new_slides_reviewed':[2,15,*range(67,82)]}
(B/'delivery_package_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8');print(json.dumps(report,ensure_ascii=False))
