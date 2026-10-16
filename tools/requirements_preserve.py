"""Snapshot/recheck real settings and WALK hashes; never log credentials."""
import argparse,base64,hashlib,html,json,re,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/requirements_audit_20261009'
def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',choices=['before','after'],required=True);p.add_argument('--output');a=p.parse_args()
    saved=json.loads((ROOT/'config/watch-access.local.json').read_text());url=saved['url'].rstrip('/')+'/'
    auth='Basic '+base64.b64encode((saved['username']+':'+saved['password']).encode()).decode()
    def read(route):
        with urllib.request.urlopen(urllib.request.Request(url+route,headers={'Authorization':auth}),timeout=10) as r:return r.read()
    text=read('').decode();fields={k:html.unescape(v) for k,v in re.findall(r"name='([^']+)'[^>]*value=\"([^\"]*)\"",text)}
    names=['led','average','idle','logging','shunt','temperature_limit','iaq_limit']
    report={'version':re.search(r'<h1>KU Watch ([\d.]+)</h1>',text)[1],'settings':{k:fields[k] for k in names},'activities':{}}
    listing=json.loads(read('activities'));report['active']=listing['active']
    if listing['active']:raise RuntimeError('Active WALK; skip update until recording stopped')
    for f in listing['files']:
        raw=read('activity?id='+str(f['id']));report['activities'][str(f['id'])]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    if a.stage=='after':
        before=json.loads((OUT/'completion_preserve_before.json').read_text())
        report['unchanged']=before['settings']==report['settings'] and before['activities']==report['activities']
    target=ROOT/a.output if a.output else OUT/('completion_preserve_'+a.stage+'.json')
    target.write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report))
if __name__=='__main__':
    try:main()
    except Exception as e:print('Preservation audit unavailable:',type(e).__name__);raise SystemExit(1)
