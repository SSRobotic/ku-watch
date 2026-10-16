"""Allowlisted user-supplied development evidence; source files are read-only."""
from pathlib import Path
from PIL import Image,ImageOps
import hashlib,json,subprocess,importlib.util
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/ppt_history_v2_20261016/build';OUT.mkdir(parents=True,exist_ok=True)
A=OUT/'assets';A.mkdir(exist_ok=True)
D=Path('C:/Users/pomma/Downloads');P=D/'06_รูปภาพ_วิดีโอ/รูปภาพ'
items=[
('cad',D/'Screenshot_2026-08-16_085113.png','แบบ CAD เปรียบเทียบ V1 กับ V5'),
('mcu',P/'791720806_2445588969298646_3046954013581369543_n.jpg','บอร์ด ESP32-S3 Super Mini'),
('layout',P/'795696844_1073419405074088_3344000959176444967_n.jpg','ทดลองจัดวางโมดูลภายในเคส'),
('battery',P/'791957796_1858566745204959_5500116975208088457_n.jpg','แบตเตอรี่ 1000 mAh และตำแหน่ง MAX30102'),
('assembly_wide',P/'797990821_28924668957141189_2118068080910346534_n.jpg','ต่อสายโมดูลและทดสอบการแสดงผล'),
('devices',P/'800924183_897757213193143_7601139544988815272_n.jpg','ตรวจอุปกรณ์จากหน้า DEVICES'),
('lcd_issue',P/'796525415_1066924072983712_4767972447123320485_n.jpg','อาการจอขาวและเส้นระหว่างพัฒนา'),
('button',P/'798261185_1643273724081390_2659566595390626202_n.jpg','ตำแหน่งปุ่มกดบนตัวเรือน'),
('usb_small',P/'775404917_957792600676297_2537321507527061915_n.jpg','ตรวจช่อง USB ของตัวเล็ก'),
('slot',P/'777664036_1595265672382878_3405743276269853523_n.jpg','ตรวจช่องและจุดยึดภายในเคส'),
('usb_hub',P/'780949188_1968225717204040_8097722767150619649_n.jpg','ตรวจระยะเสียบสายของจอใหญ่'),
('hub_marked',P/'775468132_1614136690435499_192791476956378090_n.jpg','ตรวจตำแหน่งบอร์ดจอใหญ่ในเคส'),
('hub_board',P/'792999551_1379349154344908_1489685847380201928_n.jpg','จอใหญ่พร้อมช่อง MicroSD และ RTC'),
('hub_home',P/'778230763_2537578636713856_7597434287269071384_n.jpg','หน้าหลักจอใหญ่ระยะแรก'),
('hub_system',P/'782447063_2514403358983168_5643186517549526312_n.jpg','หน้า SYSTEM ของจอใหญ่'),
('hub_brightness',P/'778659746_1291817602890222_3836565738572622969_n.jpg','หน้าปรับความสว่างด้วยระบบสัมผัส'),
('environment',P/'799777349_1427362126265470_5405579252750891170_n.jpg','อ่านค่าสภาพแวดล้อมบนตัวเล็ก'),
('open_home',P/'793900109_2008143866512784_4478929358220714283_n.jpg','ต้นแบบเปิดเคสระหว่างทดสอบ'),
('open_env',P/'794645826_38654322554181059_3092646121873405581_n.jpg','ทดสอบสภาพแวดล้อมพร้อมตรวจสาย'),
('env_angle',P/'798261185_1594153032443739_2201259088266148663_n.jpg','หน้า ENVIRONMENT ระหว่างประกอบ'),
('env_wide',P/'799427167_1065171629839536_888359591120652766_n.jpg','ทดสอบโมดูลร่วมกับจอจริง'),
('backend_photo',D/'795580942_2209165816600053_4658965607603286614_n.jpg','นาฬิกาและ Node-RED บนคอมพิวเตอร์'),
('backend_screen',D/'image.png','Node-RED dashboard และ flow ระยะแรก'),
]
report={'boundary':'Historical user-supplied development images, not acceptance-test passes. Work stages are inferred from visible content, not from dates displayed on early firmware. No evidence image is cropped or generated.','images':[],'duplicates':[],'pdfs':[]}
seen={}
for key,source,title in items:
    data=source.read_bytes();sha=hashlib.sha256(data).hexdigest()
    if sha in seen:report['duplicates'].append({'source':str(source),'same_as':seen[sha]});continue
    seen[sha]=str(source)
    im=ImageOps.exif_transpose(Image.open(source)).convert('RGB')
    target=A/(key+'.jpg');im.save(target,quality=96)
    report['images'].append({'id':key,'source':str(source),'title':title,'source_sha256':sha,'display_file':str(target),'width':im.width,'height':im.height})
for duplicate in [P/'796525415_1066924072983712_4767972447123320485_n (1).jpg',P/'795580942_2209165816600053_4658965607603286614_n.jpg']:
    sha=hashlib.sha256(duplicate.read_bytes()).hexdigest()
    assert sha in seen
    report['duplicates'].append({'source':str(duplicate),'same_as':seen[sha]})
for key,name in [('drawing','KU_Watch_Drawing.PDF'),('schematic','KU_Watch_Schematic.pdf')]:
    source=D/name
    r=subprocess.run(['pdftoppm','-png','-scale-to','3400','-singlefile',str(source),str(A/key)],capture_output=True)
    if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace'))
    text=''
    if importlib.util.find_spec('pypdf'):
        from pypdf import PdfReader
        reader=PdfReader(source);text='\n'.join(page.extract_text() or '' for page in reader.pages)
        assert len(reader.pages)==1
    (OUT/(key+'_extracted.txt')).write_text(text,'utf8')
    report['pdfs'].append({'id':key,'source':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'image':str(A/(key+'.png')),'pages':1})
v=D/'AQNdXwfSkFNrcyh--nItaImSmfYYLOgnlxG169njOdSTdjYAx4RyCfwZVPcQZ3hsR0HISavvDcaRlE-yE-oetlXMLalAFHmzj4M9AM3xig.mp4'
probe=json.loads(subprocess.run(['ffprobe','-v','error','-show_entries','format=duration:stream=codec_name,width,height','-of','json',str(v)],capture_output=True,text=True,check=True).stdout)
frames=[]
for i,t in enumerate([3,14,26]):
    target=A/f'history_video_{i}.jpg'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-ss',str(t),'-i',str(v),'-frames:v','1','-q:v','2',str(target)],check=True)
    frames.append({'at_s':t,'file':str(target)})
report['video']={'source':str(v),'sha256':hashlib.sha256(v.read_bytes()).hexdigest(),'duration_s':float(probe['format']['duration']),'streams':probe['streams'],'frames':frames}
(OUT/'history_manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
print(json.dumps({'images':len(report['images']),'duplicates':len(report['duplicates']),'pdfs':len(report['pdfs']),'video_duration_s':report['video']['duration_s'],'pdf_text_lengths':[(p['id'],len((OUT/(p['id']+'_extracted.txt')).read_text('utf8'))) for p in report['pdfs']]},ensure_ascii=False))
