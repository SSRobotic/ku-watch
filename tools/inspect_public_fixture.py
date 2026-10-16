"""Replace coincident eight-hex public fixture IDs without printing local secrets."""
from pathlib import Path
import package_delivery as p
root=Path(__file__).resolve().parents[1]
import re
file=root/'tests/test_influx_flow.cjs'
text=file.read_text();changed=0
for secret in p.known_secrets():
    value=secret.decode()
    if value not in text:continue
    if not re.fullmatch(r'[0-9a-fA-F]{8}',value):raise RuntimeError('Unexpected fixture collision')
    text=text.replace(value,'13579bdf');changed+=1
file.write_text(text)
print('Public fixture identities replaced:',changed)
