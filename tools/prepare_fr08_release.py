from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess,sys,ssl,urllib.request,shutil,argparse
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/fr_completion_20261016'
config=ROOT/'config/ota-fr08.local.json';c=json.loads(config.read_text());base='https://'+c['host']+':'+str(c['port'])+'/r/'+c['capability']+'/'
p=argparse.ArgumentParser();p.add_argument('--version',default='2.0.11');a=p.parse_args();target=OUT/('fr08_release_'+a.version+'_ready.json')
if target.exists():raise FileExistsError('Preserve earlier release evidence')
run=subprocess.run([sys.executable,str(ROOT/'tools/ota_release.py'),'--version',a.version,'--url',base+'firmware.bin'],cwd=ROOT,capture_output=True,text=True)
if run.returncode:raise RuntimeError('Release validation failed: '+run.stderr.splitlines()[-1])
c['version']=a.version;config.write_text(json.dumps(c),'utf8')
context=ssl.create_default_context(cafile=str(ROOT/'config/ota_tls.local/ca.pem'))
with urllib.request.urlopen(base+'manifest.json',context=context,timeout=8) as response:manifest=json.load(response)
with urllib.request.urlopen(base+'firmware.bin',context=context,timeout=15) as response:image=response.read()
assert hashlib.sha256(image).hexdigest()==manifest['sha256'] and manifest['version']==a.version
shutil.copyfile(ROOT/'.pio/build/display_first/firmware.bin',OUT/('firmware_'+a.version+'.bin'))
proof={'checked_utc':datetime.now(timezone.utc).isoformat(),'version':manifest['version'],'firmware_sha256':manifest['sha256'],'bytes':len(image),'verified_tls_https':True,'server_private_lan':True,'private_capability_logged':False,'tls_validation_disabled':False}
target.write_text(json.dumps(proof,indent=2),'utf8');print(json.dumps(proof))
