"""Omit PowerPoint's empty optional r:id on media actions, preserving the action.

The actual video relationships, native video shapes and all media bytes remain
unchanged. This makes relationship references explicit for package validators.
"""
from pathlib import Path
import zipfile,json,hashlib
root=Path(__file__).resolve().parents[1]
b=root/'output/ppt_academic_20261016/build'
source=b/'media_candidate.pptx';target=b/'normalized_media_candidate.pptx'
old=b'<a:hlinkClick r:id="" action="ppaction://media"/>'
new=b'<a:hlinkClick action="ppaction://media"/>'
changed=[]
with zipfile.ZipFile(source) as src,zipfile.ZipFile(target,'w') as out:
    for item in src.infolist():
        data=src.read(item.filename)
        if item.filename.startswith('ppt/slides/slide') and item.filename.endswith('.xml'):
            count=data.count(old)
            if count:changed.append({'part':item.filename,'empty_optional_media_ids_omitted':count});data=data.replace(old,new)
        out.writestr(item,data)
assert sum(x['empty_optional_media_ids_omitted'] for x in changed)==9
report={'source':str(source),'candidate':str(target),'changed':changed,'media_and_relationship_parts_unchanged':True,'sha256':hashlib.sha256(target.read_bytes()).hexdigest()}
(b/'media_normalization.json').write_text(json.dumps(report,indent=2),'utf8')
print(json.dumps({'changed_actions':9,'candidate':str(target)}))
