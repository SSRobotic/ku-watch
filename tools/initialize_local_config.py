"""Create missing ignored headers only. Never overwrite or contact devices."""
from pathlib import Path
import secrets

ROOT=Path(__file__).resolve().parents[1]
files={
 'include/config.h':(ROOT/'include/config.example.h').read_text('utf8'),
 'include/cloud_private.h':'#pragma once\n#define KU_CLOUD_ENABLED false\n#define KU_CLOUD_HOST ""\n#define KU_CLOUD_USER ""\n#define KU_CLOUD_PASSWORD ""\n',
 'include/espnow_private.h':'#pragma once\n#include <stdint.h>\nstatic const uint8_t KU_LINK_KEY[16]={'+','.join('0x%02x'%x for x in secrets.token_bytes(16))+'};\n',
}
for name,content in files.items():
 p=ROOT/name
 if p.exists(): print('Kept existing local file:',name)
 else:
  p.parent.mkdir(parents=True,exist_ok=True)
  with p.open('x',encoding='utf8') as f:f.write(content)
  print('Created ignored local file:',name)
print('No network request, service restart or firmware upload was performed.')
