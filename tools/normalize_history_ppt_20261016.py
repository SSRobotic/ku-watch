from pathlib import Path
from PIL import Image,ImageChops
import zipfile,json
root=Path(__file__).resolve().parents[1];b=root/'output/ppt_history_v2_20261016/build'
changed=[]
with zipfile.ZipFile(b/'merged_native_candidate.pptx') as src,zipfile.ZipFile(b/'normalized_candidate.pptx','w') as dst:
    for item in src.infolist():
        data=src.read(item.filename)
        if item.filename.startswith('ppt/slides/slide') and item.filename.endswith('.xml'):
            old=b'<a:hlinkClick r:id="" action="ppaction://media"/>'
            count=data.count(old)
            if count:changed.append({'part':item.filename,'optional_empty_media_id_omitted':count});data=data.replace(old,b'<a:hlinkClick action="ppaction://media"/>')
        dst.writestr(item,data)
assert sum(x['optional_empty_media_id_omitted'] for x in changed)==10
equal=[];navigation_only=[];different=[]
for n in range(1,67):
    if n in (2,15):continue
    before=root/f'output/ppt_academic_20261016/build/native_render/slide-{n:02}.png'
    after=b/f'native_render/slide-{n:02}.png'
    diff=ImageChops.difference(Image.open(before).convert('RGB'),Image.open(after).convert('RGB'))
    if diff.getbbox() is None:equal.append(n)
    elif n>=16:
        diff.paste((0,0,0),(1250,80,1545,123))
        if diff.getbbox() is None:navigation_only.append(n)
        else:different.append(n)
    else:different.append(n)
report={'normalization':changed,'unmodified_slides_pixel_identical':equal,'source_slides_with_only_navigation_added':navigation_only,'unmodified_slides_with_visual_difference':different,'new_or_revised_slides':[2,15,*range(67,82)]}
(b/'source_fidelity.json').write_text(json.dumps(report,indent=2),'utf8')
print(json.dumps({'media_actions_normalized':10,'unchanged_pixel_identical':len(equal),'only_navigation_added':len(navigation_only),'unexpected_visual_differences':different}))
