"""Inspect supplied media and retain uncropped, correctly rotated video frames."""
from pathlib import Path
import hashlib,json,subprocess,zipfile
from lxml import etree as E
from PIL import Image,ImageOps
ROOT=Path(__file__).resolve().parents[1];SRC=ROOT/'สไลด์';BUILD=ROOT/'output/ppt_academic_20261016/build';ASSETS=BUILD/'assets';ASSETS.mkdir(parents=True,exist_ok=True)
manifest={'videos':[],'photos':[],'source_decks':[]}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for i,p in enumerate(sorted(SRC.glob('*.mp4')),1):
 info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(p)],text=True));v=next(x for x in info['streams'] if x['codec_type']=='video');d=float(info['format']['duration']);item={'id':'user_'+str(i),'source':str(p.relative_to(ROOT)),'sha256':sha(p),'duration_s':d,'width':v['width'],'height':v['height'],'rotation':v.get('side_data_list',[]),'frames':[]}
 for j,fraction in enumerate([.1,.4,.75]):
  at=min(d-.1,max(.1,d*fraction));out=ASSETS/f'user_{i}_frame_{j}.jpg'
  subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-n','-ss',str(at),'-i',str(p),'-frames:v','1','-q:v','2',str(out)],check=True)
  with Image.open(out) as im:size=im.size
  item['frames'].append({'path':str(out.relative_to(ROOT)),'at_s':at,'width':size[0],'height':size[1]})
 manifest['videos'].append(item)
for i,p in enumerate(sorted(SRC.glob('*.jpg')),1):
 out=ASSETS/f'user_photo_{i}.jpg'
 with Image.open(p) as im:ImageOps.exif_transpose(im).convert('RGB').save(out,quality=95)
 with Image.open(out) as im:size=im.size
 manifest['photos'].append({'source':str(p.relative_to(ROOT)),'sha256':sha(p),'display_file':str(out.relative_to(ROOT)),'width':size[0],'height':size[1]})
for p in SRC.glob('*.pptx'):
 rows=[]
 with zipfile.ZipFile(p) as z:
  ns={'a':'http://schemas.openxmlformats.org/drawingml/2006/main','p':'http://schemas.openxmlformats.org/presentationml/2006/main'}
  root=E.fromstring(z.read('ppt/presentation.xml'));size=root.find('p:sldSz',ns)
  files=sorted([n for n in z.namelist() if __import__('re').fullmatch(r'ppt/slides/slide\d+\.xml',n)],key=lambda n:int(__import__('re').search(r'(\d+)\.xml$',n)[1]))
  for name in files:rows.append({'part':name,'text':'\n'.join(E.fromstring(z.read(name)).xpath('//a:t/text()',namespaces=ns))})
 manifest['source_decks'].append({'path':str(p.relative_to(ROOT)),'sha256':sha(p),'size':dict(size.attrib),'slides':rows})
(BUILD/'media_inventory.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(manifest,ensure_ascii=False))
