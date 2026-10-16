"""Make a short-path, ASCII-filename ZIP and an already-extracted local handoff."""
from pathlib import Path
from datetime import datetime, timezone
import csv, hashlib, html, json, shutil, zipfile

root = Path(__file__).resolve().parents[1]
delivery = root / 'output/ppt_history_v2_20261016/deliverable'
media = delivery / 'KU_Watch_พร้อมนำเสนอ_v2/ภาพและคลิป'
pptx = delivery / 'KU_Watch_นำเสนอพร้อมภาพพัฒนาการ_v2.pptx'
source_zip = delivery / 'KU_Watch_พร้อมนำเสนอ_รวมภาพพัฒนาการ_v2.zip'
expected_pptx = '99781da34e0db30aae4e2c1a5bba1565ebe1f340eb42312d6e7f4182c4353246'
expected_zip = 'bcc16bd755e3123a0881d6e7e945753ccb7b9675f5abc7ba563d0bb25583b695'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(pptx) == expected_pptx
assert sha(source_zip) == expected_zip
with zipfile.ZipFile(source_zip) as z:
    assert z.testzip() is None
manifest = json.loads((media / 'manifest.json').read_text('utf8'))
assert len(manifest['files']) == 149
for item in manifest['files']:
    assert sha(media / item['file']) == item['sha256']

downloads = Path('C:/Users/pomma/Downloads')
folder = downloads / 'KU_Watch_READY_v2'
archive = downloads / 'KU_Watch_READY_v2.zip'
assert not folder.exists() and not archive.exists(), 'Preserve existing destination files'
folder.mkdir()
shutil.copyfile(pptx, folder / 'slides.pptx')
counts = {'images': 0, 'videos': 0, 'documents': 0, 'data': 0}
new_entries = []
for item in manifest['files']:
    suffix = Path(item['file']).suffix.lower()
    category = 'videos' if suffix == '.mp4' else 'documents' if suffix == '.pdf' else 'data' if suffix == '.csv' else 'images'
    counts[category] += 1
    name = f'media/{category}/{category}_{counts[category]:03d}{suffix}'
    target = folder / name
    target.parent.mkdir(exist_ok=True, parents=True)
    shutil.copyfile(media / item['file'], target)
    assert sha(target) == item['sha256']
    new_entries.append({**item, 'original_file': item['file'], 'file': name})

ordered = sorted(new_entries, key=lambda x: (not x['original_file'].startswith(('09_', '10_', '11_')), new_entries.index(x)))
cards = []
for item in ordered:
    url = html.escape(item['file'], quote=True)
    title = html.escape(item['title'])
    if url.endswith('.mp4'):
        visual = f'<video src="{url}" controls preload="metadata"></video>'
    elif url.endswith(('.png', '.jpg', '.jpeg')):
        visual = f'<a href="{url}" target="_blank"><img src="{url}" alt="{title}" loading="lazy"></a>'
    else:
        visual = f'<a class="doc" href="{url}" target="_blank">เปิดไฟล์ {Path(url).suffix.upper()}</a>'
    cards.append(f'<article>{visual}<h2>{title}</h2><p>{html.escape(item["date"])} · {html.escape(item["scope"])}</p><a href="{url}" download>เปิดหรือบันทึกไฟล์เต็ม</a></article>')
page = '''<!doctype html><html lang="th"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>KU Watch - Media</title><style>body{margin:0;background:#eef1f5;color:#243244;font:17px "Leelawadee UI",Tahoma,sans-serif}header{background:#1e3a5f;color:#fff;padding:32px 5vw}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:20px;padding:24px}article{background:#fff;padding:16px}img,video{width:100%;height:340px;object-fit:contain;background:#152230}h2{font-size:21px}p{font-size:15px;line-height:1.7}a{color:#2469a1}.doc{display:block;padding:140px 0;text-align:center}</style><header><h1>KU Watch — ภาพและคลิปทั้งหมด</h1><p>คลิกภาพเพื่อดูเต็มขนาด เปิด slides.pptx สำหรับนำเสนอ แบบ Rev A เป็นเอกสารออกแบบเดิมและต่างจากเครื่องปัจจุบันบางจุด</p></header><main>''' + ''.join(cards) + '</main></html>'
(folder / 'gallery.html').write_text(page, 'utf8')
(folder / 'manifest.json').write_text(json.dumps({**manifest, 'files': new_entries}, ensure_ascii=False, indent=2), 'utf8')
with (folder / 'SOURCE_FILES.csv').open('w', encoding='utf-8-sig', newline='') as stream:
    writer = csv.writer(stream)
    writer.writerow(['file', 'title', 'original_file', 'sha256'])
    writer.writerows([x['file'], x['title'], x['original_file'], x['sha256']] for x in new_entries)
(folder / 'START_HERE.txt').write_text('''KU Watch — ชุดพร้อมเปิดใช้งาน v2

1. เปิด slides.pptx ใน Microsoft PowerPoint แล้วกด F5
2. เปิด gallery.html เพื่อเลือกดูภาพเต็มและคลิปทั้งหมด
3. หากเปิดจาก ZIP ให้แตกไฟล์ทั้งหมดก่อน (Extract All)

PowerPoint มี 14 หน้าหลัก และ 67 หน้าภาคผนวก รวม 81 หน้า
ภาพพัฒนาการอยู่หน้า 67–81 เปิดได้จากลิงก์ในหน้า 2 หรือสารบัญภาคผนวก
วิดีโอฝัง 10 ตำแหน่ง เล่นได้โดยไม่ใช้อินเทอร์เน็ต
มีภาพ 138 ภาพ คลิปต้นฉบับ 8 คลิป PDF 2 ฉบับ และ CSV จริง
ชื่อไฟล์ใช้ภาษาอังกฤษและโฟลเดอร์สั้น ส่วนชื่อภาพเดิมดูได้ใน SOURCE_FILES.csv
ไฟล์สื่อและ PowerPoint ตรงกับต้นฉบับทุกไบต์ ไม่มีการลดคุณภาพ
ชื่อสมาชิก บทบาท และราคาซื้อจริงยังเว้นไว้ให้เติม
แบบ Rev A เป็นเอกสารออกแบบเดิม ไม่ใช่ As-built ปัจจุบัน
เวลารับ MQTT สะสมต่างจากเวลารับต่อเนื่องและอายุแบตเตอรี่
''', 'utf8')
checks = []
for file in sorted(folder.rglob('*')):
    if file.is_file():
        checks.append(f'{sha(file)}  {file.relative_to(folder).as_posix()}')
(folder / 'SHA256SUMS.txt').write_text('\n'.join(checks) + '\n', 'utf8')
with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=False) as z:
    for file in sorted(folder.rglob('*')):
        if file.is_file():
            z.write(file, file.relative_to(downloads).as_posix())
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    assert all(n.isascii() for n in z.namelist())
    assert hashlib.sha256(z.read('KU_Watch_READY_v2/slides.pptx')).hexdigest() == expected_pptx
    for item in new_entries:
        assert hashlib.sha256(z.read('KU_Watch_READY_v2/' + item['file'])).hexdigest() == item['sha256']
    longest_name = max(map(len, z.namelist()))

# Restore the exact previously published paths as well as provide short-path copies.
ready = root / 'สไลด์/พร้อมนำเสนอ'
for source in (pptx, source_zip):
    target = ready / source.name
    if target.exists():
        assert sha(target) == sha(source), 'Preserve changed published copy'
    else:
        shutil.copyfile(source, target)
    assert sha(target) == sha(source)
result = {'created_utc': datetime.now(timezone.utc).isoformat(), 'folder': str(folder), 'archive': str(archive), 'archive_sha256': sha(archive), 'archive_bytes': archive.stat().st_size, 'counts': counts, 'presentation_sha256': expected_pptx, 'all_media_payloads_unchanged': True, 'all_archive_paths_ascii': True, 'longest_archive_path_chars': longest_name, 'restored_previous_link_paths': True}
(root / 'output/ppt_history_v2_20261016/build/zip_open_repair.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), 'utf8')
print(json.dumps(result, ensure_ascii=False))
