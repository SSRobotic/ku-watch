"""Inspect service failures with known local secret values redacted."""
from pathlib import Path
import json,re
from package_delivery import known_secrets
ROOT=Path(__file__).resolve().parents[1]
secrets=known_secrets()
for name in ['nodered.stdout.log','nodered.stderr.log','influx.stderr.log']:
    path=ROOT/'output/backend_logs'/name
    if not path.exists():continue
    lines=path.read_text(encoding='utf8',errors='replace').splitlines()
    selected=[line for line in lines if re.search('error|warn|failed|Started|Connected|connection|flows',line,re.I)][-10:]
    for secret in sorted(secrets,key=len,reverse=True):selected=[line.replace(secret.decode(),'[REDACTED]') for line in selected]
    print(json.dumps({'file':name,'lines':selected}))
settings=Path.home()/'.node-red/settings-ku-watch.js'
source=settings.read_text()
print(json.dumps({'settings_env_names':sorted(set(re.findall(r'KU_[A-Z_]+',source)))}))
