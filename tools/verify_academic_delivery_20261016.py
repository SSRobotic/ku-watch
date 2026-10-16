from pathlib import Path
import json,zipfile,hashlib,importlib.util,lxml.etree as E
root=Path(__file__).resolve().parents[1];b=root/'output/ppt_academic_20261016/build';out=b.parent/'deliverable'
deck=out/'KU_Watch_นำเสนอวิชาการ_18ตุลาคม2569.pptx'
plan=json.loads((b/'deck_plan.json').read_text('utf8'))
spec=importlib.util.spec_from_file_location('delivery',root/'tools/package_delivery.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);secrets=mod.known_secrets()
ns={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
with zipfile.ZipFile(deck) as z:
    assert z.testzip() is None
    names=z.namelist()
    slides=[x for x in names if x.startswith('ppt/slides/slide') and x.endswith('.xml')]
    assert len(slides)==66
    hidden=[x for x in slides if E.fromstring(z.read(x)).get('show')=='0'];assert len(hidden)==52
    for name in names:
        if name.endswith(('.xml','.rels')):
            data=z.read(name)
            assert not any(secret in data for secret in secrets),'Configured credential in public XML'
            if name.endswith('.rels'):
                for relationship in E.fromstring(data):
                    if any(w in relationship.get('Type','') for w in ['/video','/media','/audio']):assert relationship.get('TargetMode')!='External'
    videos={hashlib.sha256(z.read(name)).hexdigest():name for name in names if name.startswith('ppt/media/') and name.lower().endswith('.mp4')}
    assert len(videos)==9
    for job in plan['videos']:
        assert hashlib.sha256(Path(job['file']).read_bytes()).hexdigest() in videos,'Embedded media differs from original'
assert deck.read_bytes()==(b/'normalized_media_candidate.pptx').read_bytes()
play=json.loads((b/'playback_verified.json').read_text('utf-8-sig'));assert play['passed'] and len(play['videos'])==9
inventory=json.loads((b/'media_inventory.json').read_text('utf8'))
for item in inventory['videos']:
    assert hashlib.sha256((root/item['source']).read_bytes()).hexdigest()==item['sha256'],'Original user clip changed'
gallery=json.loads((out/'KU_Watch_ภาพและคลิป/manifest.json').read_text('utf8'))
for item in gallery['files']:
    assert hashlib.sha256((out/'KU_Watch_ภาพและคลิป'/item['file']).read_bytes()).hexdigest()==item['sha256']
report={'pptx':str(deck),'sha256':hashlib.sha256(deck.read_bytes()).hexdigest(),'slides':66,'main':14,'appendix_hidden':52,'embedded_original_videos':9,'actual_native_playback_passed':True,'known_configured_secret_scan_passed':True,'gallery_media_verified':len(gallery['files']),'user_clips_unchanged':True,'final_bytes_match_validated_candidate':True}
(b/'delivery_verified.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8');print(json.dumps(report,ensure_ascii=False))
