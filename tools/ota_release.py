"""Prepare a matching firmware + HTTPS manifest; never include private headers."""
from pathlib import Path
import argparse,hashlib,json,re,shutil
from urllib.parse import urlparse
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser();p.add_argument('--version',required=True)
    mode=p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--url');mode.add_argument('--template',action='store_true')
    p.add_argument('--firmware',type=Path,default=ROOT/'.pio/build/display_first/firmware.bin');a=p.parse_args()
    if not re.fullmatch(r'\d+\.\d+\.\d+',a.version):p.error('Expected a semantic version')
    if a.url:
        parsed=urlparse(a.url)
        if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password:
            p.error('The binary URL must use HTTPS without embedded credentials')
    source=re.search(r'VERSION="([\d.]+)"',(ROOT/'include/watch_extensions.h').read_text())[1]
    image=a.firmware.read_bytes()
    if a.version!=source or not image or image[0]!=0xE9 or (a.version+'\0').encode() not in image:
        p.error('Version must match current source and a version literal in an ESP firmware image')
    out=ROOT/'output/ota_release'/a.version;out.mkdir(parents=True,exist_ok=True)
    target=out/'firmware.bin';shutil.copyfile(a.firmware,target)
    digest=hashlib.sha256(target.read_bytes()).hexdigest()
    name='manifest.template.json' if a.template else 'manifest.json'
    (out/name).write_text(json.dumps({'version':a.version,'url':a.url or 'HTTPS_FIRMWARE_URL','sha256':digest},indent=2)+'\n')
    (out/'version.txt').write_text(a.version+'\n')
    report={'version':a.version,'bytes':len(image),'sha256':digest,'template':a.template,
            'boundary':'Local files only; no server started, URL deployed, or automatic update tested',
            'version_check':'Source version and ESP image version literal; Arduino app descriptor contains ESP-IDF build version'}
    (out/'release.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))
if __name__=='__main__':main()
